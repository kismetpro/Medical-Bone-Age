import os
import math
import base64
import hashlib
import hmac
import json
import requests
import secrets
import sqlite3
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

import cv2
import numpy as np
import onnxruntime
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms.functional as TF
import matplotlib.pyplot as plt
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from ultralytics import YOLO

from app.utils.gradcam import GradCAM, overlay_heatmap
from app.utils.foreign_object_detection import (
    ANOMALY_SCORE_THRESHOLD,
    build_foreign_object_detection,
)
from app.utils.growth_standards import predict_adult_height
from app.utils.notification_service import NotificationService
from app.utils.rus_chn import generate_bone_report, calc_bone_age_from_score
from dp_bone_detector_v3 import DPV3BoneDetector


# ----------------------------
# Bone Age Model (与你训练保持一致)
# ----------------------------
class BoneAgeModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = models.resnet50(weights=None)
        n_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Identity()
        self.regressor = nn.Sequential(
            nn.Linear(n_features + 1, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 1),
        )

    def forward(self, x, gender):
        feat = self.backbone(x)
        combined = torch.cat((feat, gender), dim=1)
        return self.regressor(combined)


# ----------------------------
# Joint Grading Model (单关节分级)
# ----------------------------
class JointClassifier(nn.Module):
    def __init__(self, num_classes: int):
        super().__init__()
        base = models.resnet50(weights=None)
        feat_dim = base.fc.in_features
        base.fc = nn.Identity()
        self.backbone = base
        self.classifier = nn.Linear(feat_dim, num_classes)

    def forward(self, x):
        feat = self.backbone(x)
        return self.classifier(feat)


class GRL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, lambd):
        ctx.lambd = lambd
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        return -ctx.lambd * grad_output, None


def grad_reverse(x, lambd=1.0):
    return GRL.apply(x, lambd)


class DANNHyperModel(nn.Module):
    """
    Keep exactly aligned with the training architecture in
    `参考关节分级的训练过程.py`:
    - backbone: resnet50(weights=None), fc -> Identity
    - classifier: Linear(feat_dim, num_classes)
    - domain_clf: Linear-ReLU-Dropout-Linear
    - hyper_proj: Linear(feat_dim, 128)
    """

    def __init__(self, num_classes: int):
        super().__init__()
        base = models.resnet50(weights=None)
        feat_dim = base.fc.in_features
        base.fc = nn.Identity()
        self.backbone = base

        self.classifier = nn.Linear(feat_dim, num_classes)
        self.domain_clf = nn.Sequential(
            nn.Linear(feat_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 2),
        )
        self.hyper_proj = nn.Linear(feat_dim, 128)

    def forward(self, x, lambda_grl: float = 0.0):
        f = self.backbone(x)
        cls = self.classifier(f)
        dom = self.domain_clf(grad_reverse(f, lambda_grl))
        h = self.hyper_proj(f)
        return cls, dom, h


class JointGrader:
    def __init__(self, model_dir: str, device: torch.device):
        self.model_dir = model_dir
        self.device = device
        self.models: Dict[str, Dict] = {}
        self.detect_joint_to_model = {
            "DIPFirst": "DIPFirst",
            "DIPThird": "DIP",
            "DIPFifth": "DIP",
            "PIPFirst": "PIPFirst",
            "PIPThird": "PIP",
            "PIPFifth": "PIP",
            "MCPFirst": "MCPFirst",
            "MCPSecond": "MCP",
            "MCPThird": "MCP",
            "MCPFourth": "MCP",
            "MCPFifth": "MCP",
            "MIPThird": "MIP",
            "MIPFifth": "MIP",
            "Ulna": "Ulna",
            "Radius": "Radius",
        }

    @staticmethod
    def _extract_state_dict(ckpt):
        if isinstance(ckpt, dict):
            for k in ["model_state", "state_dict", "model"]:
                if k in ckpt and isinstance(ckpt[k], dict):
                    return ckpt[k]
            if any(torch.is_tensor(v) for v in ckpt.values()):
                return ckpt
        return ckpt

    def load_all(self, joint_names: List[str]):
        loaded = 0
        for joint in joint_names:
            p = os.path.join(self.model_dir,  f"best_{joint}.pth")
            if not os.path.exists(p):
                print(f"WARNING: joint model not found: {p}")
                continue

            ckpt = torch.load(p, map_location=self.device)
            class_to_idx = ckpt.get("class_to_idx", None) if isinstance(ckpt, dict) else None
            if not class_to_idx:
                print(f"WARNING: class_to_idx missing in {p}, skip")
                continue

            num_classes = len(class_to_idx)
            idx_to_class = {v: k for k, v in class_to_idx.items()}

            # Strictly match training architecture and enforce strict load.
            m = DANNHyperModel(num_classes=num_classes)
            sd = self._extract_state_dict(ckpt)
            m.load_state_dict(sd, strict=True)
            m.to(self.device)
            m.eval()

            self.models[joint] = {
                "model": m,
                "idx_to_class": idx_to_class,
                "path": p,
            }
            loaded += 1
            print(f"Loaded joint model: {joint} ({num_classes} classes)")

        print(f"Joint models loaded: {loaded}")

    def preprocess(self, image_bytes: bytes, img_size: int, mean: np.ndarray, std: np.ndarray):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image for joint grading")

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (img_size, img_size), interpolation=cv2.INTER_LINEAR)
        img = img.astype(np.float32) / 255.0
        img = (img - mean) / std
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        img = np.ascontiguousarray(img)
        return torch.from_numpy(img).float().to(self.device)

    def preprocess_patch(self, patch_bgr: np.ndarray, img_size: int, mean: np.ndarray, std: np.ndarray):
        if patch_bgr is None or patch_bgr.size == 0:
            raise ValueError("Invalid patch for joint grading")
        patch = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2RGB)
        patch = cv2.resize(patch, (img_size, img_size), interpolation=cv2.INTER_LINEAR)
        patch = patch.astype(np.float32) / 255.0
        patch = (patch - mean) / std
        patch = np.transpose(patch, (2, 0, 1))
        patch = np.expand_dims(patch, axis=0)
        patch = np.ascontiguousarray(patch)
        return torch.from_numpy(patch).float().to(self.device)

    @staticmethod
    def _safe_crop(img_bgr: np.ndarray, bbox_xyxy: List[float], expand_ratio: float = 0.08):
        h, w = img_bgr.shape[:2]
        x1, y1, x2, y2 = bbox_xyxy
        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)
        ex = bw * expand_ratio
        ey = bh * expand_ratio
        x1 = max(0, int(round(x1 - ex)))
        y1 = max(0, int(round(y1 - ey)))
        x2 = min(w, int(round(x2 + ex)))
        y2 = min(h, int(round(y2 + ey)))
        if x2 <= x1 or y2 <= y1:
            return None
        return img_bgr[y1:y2, x1:x2].copy()
    #这里是小关节分级逻辑，去掉了对图像的预处理

    @torch.no_grad()
    def predict(self, image_bytes: bytes, img_size: int, mean: np.ndarray, std: np.ndarray):
        if not self.models:
            return {}

        x = self.preprocess(image_bytes, img_size, mean, std)
        # x =  image_bytes
        x = cv2.resize(x, (1024, 1024))
        out = {}

        for joint, item in self.models.items():
            logits, _, _ = item["model"](x, lambda_grl=0.0)
            probs = torch.softmax(logits, dim=1)
            pred_idx = int(torch.argmax(probs, dim=1).item())
            conf = float(torch.max(probs, dim=1).values.item())
            raw_cls = item["idx_to_class"].get(pred_idx, pred_idx)

            out[joint] = {
                "grade_idx": pred_idx,
                "grade_raw": int(raw_cls),
                "score": round(conf, 4),
            }

        return out

    @torch.no_grad()
    def predict_detected_joints(
        self,
        image_bytes: bytes,
        detected_joints: Dict[str, Dict],
        img_size: int,
        mean: np.ndarray,
        std: np.ndarray,
    ):
        if not self.models or not detected_joints:
            return {}

        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        #修改了size
        img_bgr = cv2.resize(img_bgr, (img_size, img_size))
        if img_bgr is None:
            raise ValueError("Could not decode image for detected-joint grading")

        out: Dict[str, Dict] = {}
        for joint_name, det in detected_joints.items():
            bbox = det.get("bbox_xyxy")
            if not bbox or len(bbox) != 4:
                continue

            model_joint = self.detect_joint_to_model.get(joint_name)
            if not model_joint:
                continue

            if model_joint not in self.models:
                out[joint_name] = {
                    "model_joint": model_joint,
                    "grade_idx": None,
                    "grade_raw": None,
                    "score": 0.0,
                    "status": "model_missing",
                }
                continue

            patch = self._safe_crop(img_bgr, bbox)
            if patch is None:
                out[joint_name] = {
                    "model_joint": model_joint,
                    "grade_idx": None,
                    "grade_raw": None,
                    "score": 0.0,
                    "status": "crop_invalid",
                }
                continue

            x = self.preprocess_patch(patch, img_size, mean, std)
            logits, _, _ = self.models[model_joint]["model"](x, lambda_grl=0.0)
            probs = torch.softmax(logits, dim=1)
            pred_idx = int(torch.argmax(probs, dim=1).item())
            conf = float(torch.max(probs, dim=1).values.item())
            raw_cls = self.models[model_joint]["idx_to_class"].get(pred_idx, pred_idx)

            out[joint_name] = {
                "model_joint": model_joint,
                "grade_idx": pred_idx,
                "grade_raw": int(raw_cls),
                "score": round(conf, 4),
                "status": "ok",
            }

        return out


# ----------------------------
# Fracture Detector
# ----------------------------
class FractureDetector:
    def __init__(self, model_path: str):
        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if torch.cuda.is_available()
            else ["CPUExecutionProvider"]
        )
        self.session = onnxruntime.InferenceSession(model_path, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.id2names = {
            0: "boneanomaly",
            1: "bonelesion",
            2: "foreignbody",
            3: "fracture",
            4: "metal",
            5: "periostealreaction",
            6: "pronatorsign",
            7: "softtissue",
            8: "text",
        }

    def detect(self, image_bytes: bytes, score_threshold: float = 0.3) -> Tuple[List[Dict], Optional[str]]:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_orig = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_orig is None:
            return [], None

        img_640 = cv2.resize(img_orig, (640, 640), interpolation=cv2.INTER_LINEAR)
        ok, buf = cv2.imencode(".jpg", img_640)
        detection_image_base64 = None
        if ok:
            detection_image_base64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")

        img = cv2.cvtColor(img_640, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, 0)
        img = np.ascontiguousarray(img)

        outputs = self.session.run([self.output_name], {self.input_name: img})[0]
        if len(outputs.shape) == 3:
            outputs = outputs[0]

        anomalies: List[Dict] = []
        for det in outputs:
            conf = float(det[4])
            if conf <= score_threshold:
                continue
            anomalies.append(
                {
                    "type": self.id2names.get(int(det[5]), "unknown"),
                    "score": round(conf, 3),
                    "coord": [
                        round(float((det[0] + det[2]) / 2 / 640), 4),
                        round(float((det[1] + det[3]) / 2 / 640), 4),
                        round(float((det[2] - det[0]) / 640), 4),
                        round(float((det[3] - det[1]) / 640), 4),
                    ],
                }
            )

        return anomalies, detection_image_base64


class SmallJointRecognizer:
    def __init__(self, model_path: str, imgsz: int = 1024, conf: float = 0.2):
        self.model = YOLO(model_path)
        self.imgsz = imgsz
        self.conf = conf

    def _render_with_plt(self, img_bgr: np.ndarray, joints: Dict[str, Dict], hand_side: str, grades: Dict[str, Dict] = None) -> Optional[str]:
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        fig, ax = plt.subplots(figsize=(8, 10), dpi=120)
        ax.imshow(img_rgb)

        for name, payload in joints.items():
            x1, y1, x2, y2 = payload["bbox_xyxy"]
            rect = plt.Rectangle(
                (x1, y1),
                x2 - x1,
                y2 - y1,
                fill=False,
                edgecolor="red",
                linewidth=2,
            )
            ax.add_patch(rect)
            
            # 基础标签：名称 + 置信度
            label = f"{name} {payload['score']:.2f}"
            
            # 如果提供了分级信息，则在标签中加入分级
            if grades and name in grades:
                grade = grades[name].get('grade_raw')
                if grade is not None:
                    label += f" G:{grade}"
            
            ax.text(
                x1,
                max(0.0, y1 - 6.0),
                label,
                color="white",
                fontsize=8,
                bbox={"facecolor": "red", "alpha": 0.65, "pad": 1.5},
            )

        ax.set_title(f"Small Joint Detect | Hand: {hand_side} | Found: {len(joints)}")
        ax.axis("off")
        fig.tight_layout()
        fig.canvas.draw()

        rgba = np.asarray(fig.canvas.buffer_rgba())
        rgb = rgba[:, :, :3].copy()
        plt.close(fig)

        plot_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        ok, buf = cv2.imencode(".jpg", plot_bgr)
        if not ok:
            return None

        return "data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")

    def recognize_13(self, image_bytes: bytes) -> Dict:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            return {"hand_side": "unknown", "detected_count": 0, "joints": {}, "plot_image_base64": None}

        h, w = img_bgr.shape[:2]
        #调试缩放比例
        img_bgr = cv2.resize(img_bgr, (self.imgsz, self.imgsz))
        result = self.model.predict(
            source=img_bgr,
            imgsz=self.imgsz,
            conf=self.conf,
            verbose=True,
        )[0]

        all_d = []
        radius_x = None
        ulna_x = None
        for box in result.boxes:
            coords = box.xyxy[0].cpu().numpy()
            cls_id = int(box.cls[0])
            lbl = result.names[cls_id]
            score = float(box.conf[0])
            cx = float((coords[0] + coords[2]) / 2.0)
            all_d.append({"lbl": lbl, "cx": cx, "box": coords, "score": score})
            if lbl == "Radius":
                radius_x = cx
            elif lbl == "Ulna":
                ulna_x = cx

        is_left = None
        if ulna_x is not None and radius_x is not None:
            is_left = ulna_x < radius_x

        final_13: Dict[str, Dict] = {}

        def map_finger_logic(
            yolo_lbl: str,
            target_prefix: str,
            finger_indices: List[int],
            target_suffixes: List[str],
        ):
            subset = [d for d in all_d if d["lbl"] == yolo_lbl]
            if is_left is None:
                subset = sorted(subset, key=lambda x: x["cx"])
            else:
                subset = sorted(subset, key=lambda x: x["cx"], reverse=not is_left)

            for idx, suffix in zip(finger_indices, target_suffixes):
                if len(subset) > idx:
                    final_13[f"{target_prefix}{suffix}"] = subset[idx]

        for d in all_d:
            if d["lbl"] == "Radius" and "Radius" not in final_13:
                final_13["Radius"] = d
            elif d["lbl"] == "Ulna" and "Ulna" not in final_13:
                final_13["Ulna"] = d

        map_finger_logic("MCP", "MCP", [0, 2, 4], ["First", "Third", "Fifth"])
        map_finger_logic("ProximalPhalanx", "PIP", [0, 2, 4], ["First", "Third", "Fifth"])
        map_finger_logic("MiddlePhalanx", "MIP", [1, 2], ["Third", "Fifth"])
        map_finger_logic("DistalPhalanx", "DIP", [0, 2, 4], ["First", "Third", "Fifth"])

        joints: Dict[str, Dict] = {}
        for name, info in final_13.items():
            b = info["box"]
            x1, y1, x2, y2 = map(float, b.tolist())
            joints[name] = {
                "type": name,
                "score": round(float(info["score"]), 4),
                "bbox_xyxy": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                "coord": [
                    round((x1 + x2) / 2.0 / w, 4),
                    round((y1 + y2) / 2.0 / h, 4),
                    round((x2 - x1) / w, 4),
                    round((y2 - y1) / h, 4),
                ],
            }

        hand_side = "unknown"
        if is_left is not None:
            hand_side = "left" if is_left else "right"

        plot_image_base64 = self._render_with_plt(img_bgr, joints, hand_side)
        return {
            "hand_side": hand_side,
            "detected_count": len(joints),
            "joints": joints,
            "plot_image_base64": plot_image_base64,
        }


# ----------------------------
# RUS semantic alignment
# ----------------------------
RUS_13 = [
    "Radius",
    "Ulna",
    "MCPFirst",
    "MCPThird",
    "MCPFifth",
    "PIPFirst",
    "PIPThird",
    "PIPFifth",
    "MIPThird",
    "MIPFifth",
    "DIPFirst",
    "DIPThird",
    "DIPFifth",
]

JOINT_TO_RUS = {
    "Radius": ["Radius"],
    "Ulna": ["Ulna"],
    "MCPFirst": ["MCPFirst"],
    "MCP": ["MCPThird", "MCPFifth"],
    "PIPFirst": ["PIPFirst"],
    "PIP": ["PIPThird", "PIPFifth"],
    "MIP": ["MIPThird", "MIPFifth"],
    "DIPFirst": ["DIPFirst"],
    "DIP": ["DIPThird", "DIPFifth"],
}

FALLBACKS = {
    "Radius": ["Ulna"],
    "Ulna": ["Radius"],
    "MCPFirst": ["MCPThird", "MCPFifth"],
    "MCPThird": ["MCPFirst", "MCPFifth"],
    "MCPFifth": ["MCPThird", "MCPFirst"],
    "PIPFirst": ["PIPThird", "PIPFifth"],
    "PIPThird": ["PIPFirst", "PIPFifth"],
    "PIPFifth": ["PIPThird", "PIPFirst"],
    "MIPThird": ["MIPFifth", "PIPThird"],
    "MIPFifth": ["MIPThird", "PIPFifth"],
    "DIPFirst": ["DIPThird", "DIPFifth"],
    "DIPThird": ["DIPFirst", "DIPFifth"],
    "DIPFifth": ["DIPThird", "DIPFirst"],
}

SCORE_TABLE = {
    "female": {
        "Radius": [0, 10, 15, 22, 25, 40, 59, 91, 125, 138, 178, 192, 199, 203, 210],
        "Ulna": [0, 27, 31, 36, 50, 73, 95, 120, 157, 168, 176, 182, 189],
        "MCPFirst": [0, 5, 7, 10, 16, 23, 28, 34, 41, 47, 53, 66],
        "MCPThird": [0, 3, 5, 6, 9, 14, 21, 32, 40, 47, 51],
        "MCPFifth": [0, 4, 5, 7, 10, 15, 22, 33, 43, 47, 51],
        "PIPFirst": [0, 6, 7, 8, 11, 17, 26, 32, 38, 45, 53, 60, 67],
        "PIPThird": [0, 3, 5, 7, 9, 15, 20, 25, 29, 35, 41, 46, 51],
        "PIPFifth": [0, 4, 5, 7, 11, 18, 21, 25, 29, 34, 40, 45, 50],
        "MIPThird": [0, 4, 5, 7, 10, 16, 21, 25, 29, 35, 43, 46, 51],
        "MIPFifth": [0, 3, 5, 7, 12, 19, 23, 27, 32, 35, 39, 43, 49],
        "DIPFirst": [0, 5, 6, 8, 10, 20, 31, 38, 44, 45, 52, 67],
        "DIPThird": [0, 3, 5, 7, 10, 16, 24, 30, 33, 36, 39, 49],
        "DIPFifth": [0, 5, 6, 7, 11, 18, 25, 29, 33, 35, 39, 49],
    },
    "male": {
        "Radius": [0, 8, 11, 15, 18, 31, 46, 76, 118, 135, 171, 188, 197, 201, 209],
        "Ulna": [0, 25, 30, 35, 43, 61, 80, 116, 157, 168, 180, 187, 194],
        "MCPFirst": [0, 4, 5, 8, 16, 22, 26, 34, 39, 45, 52, 66],
        "MCPThird": [0, 3, 4, 5, 8, 13, 19, 30, 38, 44, 51],
        "MCPFifth": [0, 3, 4, 6, 9, 14, 19, 31, 41, 46, 50],
        "PIPFirst": [0, 4, 5, 7, 11, 17, 23, 29, 36, 44, 52, 59, 66],
        "PIPThird": [0, 3, 4, 5, 8, 14, 19, 23, 28, 34, 40, 45, 50],
        "PIPFifth": [0, 3, 4, 6, 10, 16, 19, 24, 28, 33, 40, 44, 50],
        "MIPThird": [0, 3, 4, 5, 9, 14, 18, 23, 28, 35, 42, 45, 50],
        "MIPFifth": [0, 3, 4, 6, 11, 17, 21, 26, 31, 36, 40, 43, 49],
        "DIPFirst": [0, 4, 5, 6, 9, 19, 28, 36, 43, 46, 51, 67],
        "DIPThird": [0, 3, 4, 5, 9, 15, 23, 29, 33, 37, 40, 49],
        "DIPFifth": [0, 3, 4, 6, 11, 17, 23, 29, 32, 36, 40, 49],
    },
}


def _map_grade_to_stage(grade_raw: int, max_stage: int) -> int:
    g = max(1, int(grade_raw))
    stage = round((g - 1) / 13.0 * max_stage)
    return int(max(0, min(stage, max_stage)))


def align_joint_semantics(joint_grades: Dict) -> Dict:
    aligned: Dict[str, Dict] = {}

    for src_joint, payload in joint_grades.items():
        if payload.get("grade_raw", None) is None:
            continue
        if src_joint in RUS_13:
            targets = [src_joint]
        else:
            targets = JOINT_TO_RUS.get(src_joint, [])
        for t in targets:
            aligned[t] = {
                "grade_raw": int(payload.get("grade_raw", 1)),
                "score": float(payload.get("score", 0.0)),
                "source_joint": src_joint,
                "imputed": False,
            }

    for rus_joint in RUS_13:
        if rus_joint in aligned:
            continue
        cand = FALLBACKS.get(rus_joint, [])
        picked = None
        for c in cand:
            if c in aligned:
                picked = c
                break
        if picked is not None:
            aligned[rus_joint] = {
                "grade_raw": aligned[picked]["grade_raw"],
                "score": aligned[picked]["score"] * 0.95,
                "source_joint": aligned[picked]["source_joint"],
                "imputed": True,
            }
        else:
            aligned[rus_joint] = {
                "grade_raw": 1,
                "score": 0.0,
                "source_joint": "none",
                "imputed": True,
            }

    return aligned


def calc_rus_score(aligned_13: Dict, gender: str):
    g = "male" if gender == "male" else "female"
    details = []
    total_score = 0

    for joint in RUS_13:
        score_list = SCORE_TABLE[g][joint]
        max_stage = len(score_list) - 1
        grade_raw = int(aligned_13[joint]["grade_raw"])
        stage = _map_grade_to_stage(grade_raw, max_stage)
        score = int(score_list[stage])
        total_score += score

        details.append(
            {
                "joint": joint,
                "grade_raw": grade_raw,
                "stage": stage,
                "score": score,
                "imputed": bool(aligned_13[joint]["imputed"]),
                "source_joint": aligned_13[joint]["source_joint"],
            }
        )

    return total_score, details


def semantic_align_missing_joint_grades(joint_grades: Dict) -> Dict:
    """
    对没有对应模型或裁剪失败的关节做语义补全。
    规则:
    - 仅补全 grade_raw 为空的关节
    - 使用 FALLBACKS 中的候选关节
    - 置信度做轻微折减，并标记 imputed
    """
    if not joint_grades:
        return {}

    aligned = dict(joint_grades)
    for joint in RUS_13:
        payload = aligned.get(joint)
        if payload and payload.get("grade_raw", None) is not None:
            payload["imputed"] = False
            aligned[joint] = payload
            continue

        picked = None
        for cand in FALLBACKS.get(joint, []):
            c = aligned.get(cand)
            if c and c.get("grade_raw", None) is not None:
                picked = c
                picked_name = cand
                break

        if picked is None:
            base = payload if isinstance(payload, dict) else {}
            aligned[joint] = {
                "model_joint": base.get("model_joint", None),
                "grade_idx": None,
                "grade_raw": 1,
                "score": 0.0,
                "status": "semantic_default",
                "imputed": True,
                "source_joint": "none",
            }
            continue

        base_score = float(picked.get("score", 0.0))
        aligned[joint] = {
            "model_joint": picked.get("model_joint", None),
            "grade_idx": picked.get("grade_idx", None),
            "grade_raw": int(picked.get("grade_raw", 1)),
            "score": round(base_score * 0.95, 4),
            "status": "semantic_imputed",
            "imputed": True,
            "source_joint": picked_name,
        }

    return aligned


# ----------------------------
# Config
# ----------------------------
FOLD_MODEL_PATHS = [
    "app/models/model_fold_0.pth",
    "app/models/model_fold_1.pth",
    "app/models/model_fold_2.pth",
    "app/models/model_fold_3.pth",
    "app/models/model_fold_4.pth",
]
EXTRA_FOLD_CANDIDATES = [
    "app/models/model_fold_0 (1).pth",
    "app/models/model_fold_1 (1).pth",
    "app/models/model_fold_2 (1).pth",
    "app/models/model_fold_3 (1).pth",
    "app/models/model_fold_4 (1).pth",
]

JOINT_MODEL_DIR = os.getenv("JOINT_MODEL_DIR", "app/models/joints")
JOINT_NAMES = ["DIP", "DIPFirst", "PIP", "PIPFirst", "MCP", "MCPFirst", "MIP", "Radius", "Ulna"]

DEFAULT_AGE_MIN = 1.0
DEFAULT_AGE_MAX = 228.0

IMG_SIZE = 256
JOINT_IMG_SIZE = 1024
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

FRACTURE_MODEL_PATH = os.getenv(
    "FRACTURE_MODEL_PATH",
    "app/detector_of_bone/weight/yolov7-p6-bonefracture.onnx",
)
JOINT_RECOGNIZE_MODEL_PATH = os.getenv("JOINT_RECOGNIZE_MODEL_PATH", "app/models/recognize/best.pt")
AUTH_DB_PATH = os.getenv("AUTH_DB_PATH", "app/data/auth.db")
PREDICTION_DB_PATH = os.getenv("PREDICTION_DB_PATH", "app/data/predictions.db")
AUTH_TOKEN_EXPIRE_HOURS = int(os.getenv("AUTH_TOKEN_EXPIRE_HOURS", "24"))
PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "210000"))
LEGACY_ADMIN_REGISTER_KEY = os.getenv("ADMIN_REGISTER_KEY", "")
LEGACY_ADMIN_SELF_REGISTER_ENABLED = os.getenv("ADMIN_SELF_REGISTER_ENABLED", "false").lower() == "true"
DOCTOR_REGISTER_KEY = os.getenv("DOCTOR_REGISTER_KEY", LEGACY_ADMIN_REGISTER_KEY)
DOCTOR_SELF_REGISTER_ENABLED = os.getenv(
    "DOCTOR_SELF_REGISTER_ENABLED",
    "true" if LEGACY_ADMIN_SELF_REGISTER_ENABLED else "false",
).lower() == "true"
SUPER_ADMIN_INIT_PASSWORD = os.getenv("SUPER_ADMIN_INIT_PASSWORD", "").strip()
DEFAULT_SUPER_ADMIN_USERNAME = "admin"
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "boneage_session")
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
AUTH_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()
ALLOWED_ORIGINS = [
    item.strip()
    for item in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",")
    if item.strip()
]
ALLOWED_ORIGIN_REGEX = os.getenv(
    "ALLOWED_ORIGIN_REGEX",
    r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
).strip()
ALLOWED_HOSTS = [
    item.strip()
    for item in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if item.strip()
]
AUTH_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "300"))
AUTH_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("AUTH_RATE_LIMIT_MAX_ATTEMPTS", "10"))
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()

ROLE_USER = "user"
ROLE_DOCTOR = "doctor"
ROLE_SUPER_ADMIN = "super_admin"
VALID_ROLES = {ROLE_USER, ROLE_DOCTOR, ROLE_SUPER_ADMIN}
LEGACY_ROLE_MAP = {
    "user": ROLE_USER,
    "admin": ROLE_DOCTOR,
    "doctor": ROLE_DOCTOR,
    "super_admin": ROLE_SUPER_ADMIN,
}
ROLE_LEVELS = {
    ROLE_USER: 1,
    ROLE_DOCTOR: 2,
    ROLE_SUPER_ADMIN: 3,
}

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
models_ensemble: List[Dict] = []
fracture_detector: Optional[FractureDetector] = None
joint_grader: Optional[JointGrader] = None
joint_recognizer: Optional[SmallJointRecognizer] = None
dpv3_detector: Optional[DPV3BoneDetector] = None


# ----------------------------
# Load helpers
# ----------------------------
def _extract_state_dict(ckpt):
    if isinstance(ckpt, dict):
        if "state_dict" in ckpt:
            return ckpt["state_dict"]
        if any(torch.is_tensor(v) for v in ckpt.values()):
            return ckpt
    return ckpt


def _extract_min_max(ckpt):
    if isinstance(ckpt, dict):
        age_min = ckpt.get("age_min", DEFAULT_AGE_MIN)
        age_max = ckpt.get("age_max", DEFAULT_AGE_MAX)
        return float(age_min), float(age_max)
    return DEFAULT_AGE_MIN, DEFAULT_AGE_MAX


def load_fold_model(weight_path: str):
    ckpt = torch.load(weight_path, map_location=device)
    state_dict = _extract_state_dict(ckpt)
    age_min, age_max = _extract_min_max(ckpt)

    model = BoneAgeModel()
    model.load_state_dict(state_dict, strict=True)
    model.to(device)
    model.eval()
    return model, age_min, age_max


def list_existing_fold_paths():
    all_paths = FOLD_MODEL_PATHS + EXTRA_FOLD_CANDIDATES
    exists = [p for p in all_paths if os.path.exists(p)]
    seen = set()
    uniq = []
    for p in exists:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq


# ----------------------------
# FastAPI lifecycle
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global models_ensemble, fracture_detector, joint_grader, joint_recognizer, dpv3_detector

    init_auth_db()
    init_prediction_db()

    print(f"Loading models on {device}...")

    fracture_detector = None
    if FRACTURE_MODEL_PATH and os.path.exists(FRACTURE_MODEL_PATH):
        try:
            fracture_detector = FractureDetector(FRACTURE_MODEL_PATH)
            print(f"Fracture model loaded: {FRACTURE_MODEL_PATH}")
        except Exception as exc:
            print(f"Failed to load fracture model: {exc}")
    else:
        print(f"WARNING: Fracture model not found: {FRACTURE_MODEL_PATH}")

    models_ensemble = []
    existing = list_existing_fold_paths()
    if not existing:
        print("WARNING: No fold model file found under app/models")

    for p in existing:
        try:
            m, age_min, age_max = load_fold_model(p)
            models_ensemble.append({"model": m, "age_min": age_min, "age_max": age_max, "path": p})
            print(f"Loaded fold model: {p}, min={age_min}, max={age_max}")
        except Exception as exc:
            print(f"Error loading fold model {p}: {exc}")

    if not models_ensemble:
        print("ERROR: No age model loaded!")

    joint_grader = JointGrader(model_dir=JOINT_MODEL_DIR, device=device)
    try:
        joint_grader.load_all(joint_names=JOINT_NAMES)
    except Exception as exc:
        print(f"Failed to load joint models: {exc}")
        joint_grader = None

    joint_recognizer = None
    if JOINT_RECOGNIZE_MODEL_PATH and os.path.exists(JOINT_RECOGNIZE_MODEL_PATH):
        try:
            joint_recognizer = SmallJointRecognizer(JOINT_RECOGNIZE_MODEL_PATH)
            print(f"Joint recognize model loaded: {JOINT_RECOGNIZE_MODEL_PATH}")
        except Exception as exc:
            print(f"Failed to load joint recognize model: {exc}")
    else:
        print(f"WARNING: Joint recognize model not found: {JOINT_RECOGNIZE_MODEL_PATH}")

    dpv3_detector = None
    try:
        dpv3_detector = DPV3BoneDetector(conf=0.5, imgsz=1024)
        print(f"✅ DP V3 bone detector loaded successfully")
    except Exception as exc:
        print(f"Failed to load DP V3 detector: {exc}")

    yield

    models_ensemble = []
    fracture_detector = None
    joint_grader = None
    joint_recognizer = None
    dpv3_detector = None


app = FastAPI(title="Bone Age Assessment API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS or ["127.0.0.1", "localhost"])


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    # response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    # response.headers["Cross-Origin-Resource-Policy"] = "same-site"
    # CSP kept permissive enough for current inline static pages.
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' http: https:; frame-ancestors 'none';"
    return response


# ----------------------------
# Auth DB
# ----------------------------
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    return dt.isoformat()


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def get_auth_conn() -> sqlite3.Connection:
    db_dir = os.path.dirname(AUTH_DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_prediction_conn() -> sqlite3.Connection:
    db_dir = os.path.dirname(PREDICTION_DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(PREDICTION_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_role_value(role: Any) -> str:
    raw = str(role or "").strip().lower()
    return LEGACY_ROLE_MAP.get(raw, raw)


def _is_valid_role(role: Any) -> bool:
    return _normalize_role_value(role) in VALID_ROLES


def _role_level(role: Any) -> int:
    return ROLE_LEVELS.get(_normalize_role_value(role), 0)


def _is_doctor_or_above(role: Any) -> bool:
    return _role_level(role) >= ROLE_LEVELS[ROLE_DOCTOR]


def _create_users_table(conn: sqlite3.Connection, table_name: str = "users"):
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL CHECK (role IN ('user','doctor','super_admin')),
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            iterations INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


def _create_sessions_table(conn: sqlite3.Connection, table_name: str = "sessions"):
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user','doctor','super_admin')),
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_user_id ON {table_name}(user_id)")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_expires_at ON {table_name}(expires_at)")


def _table_sql(conn: sqlite3.Connection, table_name: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    if not row or not row["sql"]:
        return ""
    return str(row["sql"]).lower()


def _auth_role_migration_needed(conn: sqlite3.Connection) -> bool:
    users_sql = _table_sql(conn, "users")
    sessions_sql = _table_sql(conn, "sessions")
    if ROLE_DOCTOR not in users_sql or ROLE_SUPER_ADMIN not in users_sql:
        return True
    if ROLE_DOCTOR not in sessions_sql or ROLE_SUPER_ADMIN not in sessions_sql:
        return True

    legacy_users = conn.execute("SELECT COUNT(1) FROM users WHERE role = 'admin'").fetchone()
    if legacy_users and int(legacy_users[0]) > 0:
        return True

    legacy_sessions = conn.execute("SELECT COUNT(1) FROM sessions WHERE role = 'admin'").fetchone()
    if legacy_sessions and int(legacy_sessions[0]) > 0:
        return True
    return False


def _set_autoincrement_seed(conn: sqlite3.Connection, table_name: str):
    seq_table = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
    ).fetchone()
    if not seq_table:
        return
    max_row = conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}").fetchone()
    max_id = int(max_row[0]) if max_row else 0
    conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table_name,))
    conn.execute("INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table_name, max_id))


def _migrate_auth_role_schema(conn: sqlite3.Connection):
    users = conn.execute(
        """
        SELECT id, username, role, password_hash, password_salt, iterations, created_at
        FROM users
        ORDER BY id ASC
        """
    ).fetchall()

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DROP TABLE IF EXISTS users_new")
    _create_users_table(conn, "users_new")

    conn.executemany(
        """
        INSERT INTO users_new (id, username, role, password_hash, password_salt, iterations, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                int(row["id"]),
                row["username"],
                ROLE_SUPER_ADMIN
                if row["username"] == DEFAULT_SUPER_ADMIN_USERNAME
                else (_normalize_role_value(row["role"]) if _is_valid_role(row["role"]) else ROLE_USER),
                row["password_hash"],
                row["password_salt"],
                int(row["iterations"]),
                row["created_at"],
            )
            for row in users
        ],
    )

    conn.execute("DROP TABLE IF EXISTS sessions")
    conn.execute("DROP TABLE users")
    conn.execute("ALTER TABLE users_new RENAME TO users")
    _set_autoincrement_seed(conn, "users")
    _create_sessions_table(conn, "sessions")
    conn.execute("PRAGMA foreign_keys = ON")
    print("Auth role schema migrated to user/doctor/super_admin and sessions were cleared")


def _generate_bootstrap_super_admin_password() -> str:
    return f"Aa1{secrets.token_urlsafe(12)}"


def _ensure_default_super_admin(conn: sqlite3.Connection):
    row = conn.execute(
        "SELECT id, role FROM users WHERE username = ?",
        (DEFAULT_SUPER_ADMIN_USERNAME,),
    ).fetchone()
    if row:
        normalized_role = _normalize_role_value(row["role"])
        if normalized_role != ROLE_SUPER_ADMIN:
            conn.execute(
                "UPDATE users SET role = ? WHERE id = ?",
                (ROLE_SUPER_ADMIN, int(row["id"])),
            )
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (int(row["id"]),))
            print(f"Promoted '{DEFAULT_SUPER_ADMIN_USERNAME}' to super_admin")
        return

    bootstrap_password = SUPER_ADMIN_INIT_PASSWORD or _generate_bootstrap_super_admin_password()
    if not _validate_password_strength(bootstrap_password):
        raise RuntimeError("SUPER_ADMIN_INIT_PASSWORD must include upper/lower letters and digits, minimum 8 chars")
    salt_hex = secrets.token_hex(16)
    pw_hash = hash_password(bootstrap_password, salt_hex, PBKDF2_ITERATIONS)
    now_iso = _to_iso(_utc_now())
    conn.execute(
        """
        INSERT INTO users (username, role, password_hash, password_salt, iterations, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            DEFAULT_SUPER_ADMIN_USERNAME,
            ROLE_SUPER_ADMIN,
            pw_hash,
            salt_hex,
            PBKDF2_ITERATIONS,
            now_iso,
        ),
    )
    if SUPER_ADMIN_INIT_PASSWORD:
        print(f"Created bootstrap super admin '{DEFAULT_SUPER_ADMIN_USERNAME}' from SUPER_ADMIN_INIT_PASSWORD")
    else:
        print(
            f"Created bootstrap super admin '{DEFAULT_SUPER_ADMIN_USERNAME}'. "
            f"Temporary password: {bootstrap_password}"
        )


def _ensure_builtin_accounts(conn: sqlite3.Connection):
    """Ensure standard built-in accounts exist and have the correct passwords: admin, doctor, user."""
    builtin = [
        ("admin", "Admin123456", ROLE_SUPER_ADMIN),
        ("doctor", "Doctor123456", ROLE_DOCTOR),
        ("user", "User123456", ROLE_USER),
    ]
    now_iso = _to_iso(_utc_now())
    for username, password, role in builtin:
        salt_hex = secrets.token_hex(16)
        pw_hash = hash_password(password, salt_hex, PBKDF2_ITERATIONS)
        
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            conn.execute(
                """
                INSERT INTO users (username, role, password_hash, password_salt, iterations, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username, role, pw_hash, salt_hex, PBKDF2_ITERATIONS, now_iso),
            )
            print(f"Created built-in account '{username}' with role '{role}'")
        else:
            # Force update role and password to match requested built-in credentials
            conn.execute(
                """
                UPDATE users 
                SET role = ?, password_hash = ?, password_salt = ?, iterations = ?
                WHERE username = ?
                """,
                (role, pw_hash, salt_hex, PBKDF2_ITERATIONS, username),
            )
            # Invalidate existing sessions for security
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
            print(f"Refreshed built-in account '{username}' (role '{role}')")


def init_auth_db():
    with get_auth_conn() as conn:
        _create_users_table(conn)
        _create_sessions_table(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS qa_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER NOT NULL,
                owner_username TEXT NOT NULL,
                question_text TEXT NOT NULL,
                image_base64 TEXT NOT NULL,
                reply_text TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(owner_user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qa_owner_user_id ON qa_questions(owner_user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qa_created_at ON qa_questions(created_at)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(author_id) REFERENCES users(id)
            )
            """
        )
        if _auth_role_migration_needed(conn):
            _migrate_auth_role_schema(conn)
        _ensure_builtin_accounts(conn)
        _ensure_default_super_admin(conn)
        conn.commit()


def init_prediction_db():
    with get_prediction_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                filename TEXT NOT NULL,
                predicted_age_months REAL NOT NULL,
                predicted_age_years REAL NOT NULL,
                gender TEXT NOT NULL,
                real_age_years REAL,
                predicted_adult_height REAL,
                full_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_user_id ON predictions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bone_age_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                point_time INTEGER NOT NULL,
                bone_age_years REAL NOT NULL,
                chronological_age_years REAL,
                source TEXT NOT NULL DEFAULT 'manual',
                prediction_id TEXT,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bone_age_points_user_id ON bone_age_points(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bone_age_points_point_time ON bone_age_points(point_time)")
        conn.commit()

    # One-way migration from legacy predictions table in auth DB.
    try:
        with get_prediction_conn() as pred_conn:
            pred_count = int(pred_conn.execute("SELECT COUNT(1) FROM predictions").fetchone()[0])
            if pred_count > 0:
                return

        with get_auth_conn() as auth_conn:
            legacy = auth_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='predictions'"
            ).fetchone()
            if not legacy:
                return
            rows = auth_conn.execute(
                """
                SELECT id, user_id, timestamp, filename, predicted_age_months, predicted_age_years, gender, real_age_years, predicted_adult_height, full_json
                FROM predictions
                """
            ).fetchall()
            if not rows:
                return

        with get_prediction_conn() as pred_conn:
            pred_conn.executemany(
                """
                INSERT OR IGNORE INTO predictions (id, user_id, timestamp, filename, predicted_age_months, predicted_age_years, gender, real_age_years, predicted_adult_height, full_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r["id"],
                        r["user_id"],
                        r["timestamp"],
                        r["filename"],
                        r["predicted_age_months"],
                        r["predicted_age_years"],
                        r["gender"],
                        r["real_age_years"],
                        r["predicted_adult_height"],
                        r["full_json"],
                    )
                    for r in rows
                ],
            )
            pred_conn.commit()
            print(f"Migrated {len(rows)} legacy predictions into {PREDICTION_DB_PATH}")
    except Exception as exc:
        print(f"Legacy prediction migration skipped: {exc}")


def hash_password(password: str, salt_hex: str, iterations: int) -> str:
    raw = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        iterations,
    )
    return raw.hex()


def verify_password(password: str, salt_hex: str, iterations: int, expected_hash: str) -> bool:
    computed = hash_password(password, salt_hex, iterations)
    return hmac.compare_digest(computed, expected_hash)


def cleanup_expired_sessions(conn: sqlite3.Connection):
    now_iso = _to_iso(_utc_now())
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_iso,))


def create_session(conn: sqlite3.Connection, user_id: int, role: str) -> Dict[str, Any]:
    token = secrets.token_urlsafe(32)
    now = _utc_now()
    expires_at = now + timedelta(hours=AUTH_TOKEN_EXPIRE_HOURS)
    cleanup_expired_sessions(conn)
    conn.execute(
        """
        INSERT INTO sessions (token, user_id, role, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (token, user_id, role, _to_iso(expires_at), _to_iso(now)),
    )
    conn.commit()
    return {"token": token, "expires_at": _to_iso(expires_at)}


def get_session(conn: sqlite3.Connection, token: str) -> Optional[sqlite3.Row]:
    cleanup_expired_sessions(conn)
    row = conn.execute(
        """
        SELECT s.token, s.user_id, s.role, s.expires_at, u.username
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ?
        """,
        (token,),
    ).fetchone()
    if not row:
        return None

    if _from_iso(row["expires_at"]) <= _utc_now():
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        return None
    return row


_auth_rate_bucket: Dict[str, deque] = {}


def _validate_username(username: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", username))


def _validate_password_strength(password: str) -> bool:
    if len(password) < 8:
        return False
    has_upper = any(ch.isupper() for ch in password)
    has_lower = any(ch.islower() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    return has_upper and has_lower and has_digit


def _check_auth_rate_limit(request: Request, scope: str):
    host = request.client.host if request.client else "unknown"
    key = f"{scope}:{host}"
    now = _utc_now().timestamp()
    bucket = _auth_rate_bucket.setdefault(key, deque())
    while bucket and now - bucket[0] > AUTH_RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= AUTH_RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many requests, please retry later")
    bucket.append(now)


def _set_auth_cookie(response: Response, token: str, expires_at_iso: str):
    expires_dt = _from_iso(expires_at_iso)
    max_age = max(int((expires_dt - _utc_now()).total_seconds()), 0)
    samesite = AUTH_COOKIE_SAMESITE if AUTH_COOKIE_SAMESITE in {"lax", "strict", "none"} else "lax"
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=samesite,
        max_age=max_age,
        path="/",
    )


def _clear_auth_cookie(response: Response):
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")


def _resolve_token(request: Request, payload_token: Optional[str]) -> Optional[str]:
    cookie_token = request.cookies.get(AUTH_COOKIE_NAME)
    if cookie_token:
        return cookie_token
    if payload_token:
        return payload_token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if not token or token.lower() in {"null", "undefined", "none"}:
            return None
        return token
    return None


# ----------------------------
# Utils
# ----------------------------
MAX_UPLOAD_IMAGE_BYTES = 20 * 1024 * 1024


def validate_image_content(image_bytes: bytes) -> np.ndarray:
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image file is empty")
    if len(image_bytes) > MAX_UPLOAD_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image file is too large")

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image content")
    if img.ndim != 3 or img.shape[0] < 8 or img.shape[1] < 8:
        raise HTTPException(status_code=400, detail="Image dimensions are invalid")

    return img


def preprocess_image_bytes(image_bytes: bytes, brightness: float = 0.0, contrast: float = 1.0) -> bytes:
    img = validate_image_content(image_bytes)
    
    if contrast != 1.0 or brightness != 0.0:
        img = cv2.convertScaleAbs(img, alpha=contrast, beta=brightness)
    
    ok, buffer = cv2.imencode(".jpg", img)
    if not ok:
        raise ValueError("Could not encode image")
    return buffer.tobytes()

def preprocess_image(image_bytes: bytes, brightness: float = 0.0, contrast: float = 1.0):
    img = validate_image_content(image_bytes)
    
    # 应用图像增强: contrast (alpha) 和 brightness (beta)
    # 建议对比度 13.24
    if contrast != 1.0 or brightness != 0.0:
        img = cv2.convertScaleAbs(img, alpha=contrast, beta=brightness)

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 步骤2: Resize 到 256×256
    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_LINEAR)
    

    # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # img = cv2.resize(img, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_LINEAR)
    img = img.astype(np.float32) / 255.0
    img = (img - IMAGENET_MEAN) / IMAGENET_STD
    img = np.transpose(img, (2, 0, 1))
    img = np.expand_dims(img, axis=0)
    img = np.ascontiguousarray(img)
    return torch.from_numpy(img).float()


def predict_with_ensemble_tta_months(img_tensor: torch.Tensor, gender_tensor: torch.Tensor):
    if not models_ensemble:
        raise RuntimeError("No age model loaded")

    with torch.no_grad():
        img_r1 = TF.rotate(img_tensor, -5)
        img_r2 = TF.rotate(img_tensor, 5)

        fold_months = []
        for item in models_ensemble:
            m = item["model"]
            age_min = item["age_min"]
            age_max = item["age_max"]

            s1 = m(img_tensor, gender_tensor).item()
            s2 = m(img_r1, gender_tensor).item()
            s3 = m(img_r2, gender_tensor).item()

            fold_norm = (s1 + s2 + s3) / 3.0
            fold_month = fold_norm * (age_max - age_min) + age_min
            fold_months.append(fold_month)

        return float(np.mean(fold_months))


def build_gradcam_heatmap(img_tensor: torch.Tensor, gender_tensor: torch.Tensor):
    if not models_ensemble:
        return None

    try:
        cam_model = models_ensemble[0]["model"]
        target = cam_model.backbone.layer4[-1]

        img_cam = img_tensor.clone().detach()
        img_cam.requires_grad = True

        grad_cam = GradCAM(cam_model, target)
        _, cam_mask = grad_cam(img_cam, gender_tensor)

        target._forward_hooks.clear()
        target._backward_hooks.clear()

        heatmap_img = overlay_heatmap(img_cam.detach().cpu(), cam_mask)
        ok, buffer = cv2.imencode(".jpg", heatmap_img)
        if not ok:
            return None

        heatmap_b64 = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/jpeg;base64,{heatmap_b64}"
    except Exception as exc:
        print(f"GradCAM failed: {exc}")
        return None


# ----------------------------
# Endpoints
# ----------------------------
@app.get("/")
def read_root():
    return {"message": "Bone Age Assessment API is running"}


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str
    admin_key: Optional[str] = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str


class TokenRequest(BaseModel):
    token: Optional[str] = Field(default=None, min_length=20, max_length=256)


class AccountCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str


class AccountRoleUpdateRequest(BaseModel):
    role: str


def _parse_role_or_raise(raw_role: str, allowed_roles: set[str]) -> str:
    role = _normalize_role_value(raw_role)
    if role not in allowed_roles:
        allowed_display = "', '".join(sorted(allowed_roles))
        raise HTTPException(status_code=400, detail=f"Role must be one of '{allowed_display}'")
    return role


@app.post("/auth/register")
def auth_register(payload: RegisterRequest, request: Request, response: Response):
    _check_auth_rate_limit(request, "register")
    role = _parse_role_or_raise(payload.role, {ROLE_USER, ROLE_DOCTOR})

    username = payload.username.strip()
    if not _validate_username(username):
        raise HTTPException(status_code=400, detail="Username format invalid")
    if not _validate_password_strength(payload.password):
        raise HTTPException(status_code=400, detail="Password must include upper/lower letters and digits, minimum 8 chars")

    if role == ROLE_DOCTOR:
        if not DOCTOR_SELF_REGISTER_ENABLED:
            raise HTTPException(status_code=403, detail="Doctor self-register is disabled")
        if DOCTOR_REGISTER_KEY and payload.admin_key != DOCTOR_REGISTER_KEY:
            raise HTTPException(status_code=403, detail="Access denied")

    salt_hex = secrets.token_hex(16)
    pw_hash = hash_password(payload.password, salt_hex, PBKDF2_ITERATIONS)
    now_iso = _to_iso(_utc_now())

    try:
        with get_auth_conn() as conn:
            conn.execute(
                """
                INSERT INTO users (username, role, password_hash, password_salt, iterations, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username, role, pw_hash, salt_hex, PBKDF2_ITERATIONS, now_iso),
            )
            user_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            session_data = create_session(conn, user_id, role)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already exists")

    _set_auth_cookie(response, session_data["token"], session_data["expires_at"])
    return {
        "success": True,
        "message": "Register success",
        "token": session_data["token"],
        "expires_at": session_data["expires_at"],
        "username": username,
        "role": role,
    }


@app.post("/auth/login")
def auth_login(payload: LoginRequest, request: Request, response: Response):
    _check_auth_rate_limit(request, "login")
    role = _parse_role_or_raise(payload.role, VALID_ROLES)

    username = payload.username.strip()
    if not _validate_username(username):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    with get_auth_conn() as conn:
        row = conn.execute(
            """
            SELECT id, username, role, password_hash, password_salt, iterations
            FROM users
            WHERE username = ? AND role = ?
            """,
            (username, role),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        ok = verify_password(
            payload.password,
            row["password_salt"],
            int(row["iterations"]),
            row["password_hash"],
        )
        if not ok:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        session_data = create_session(conn, int(row["id"]), role)

    _set_auth_cookie(response, session_data["token"], session_data["expires_at"])
    return {
        "success": True,
        "message": "Login success",
        "token": session_data["token"],
        "expires_at": session_data["expires_at"],
        "username": row["username"],
        "role": role,
    }


@app.post("/auth/verify")
def auth_verify(payload: TokenRequest, request: Request):
    token = _resolve_token(request, payload.token)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    with get_auth_conn() as conn:
        session_row = get_session(conn, token)
        if not session_row:
            raise HTTPException(status_code=401, detail="Session expired or invalid")

        return {
            "success": True,
            "username": session_row["username"],
            "role": session_row["role"],
            "expires_at": session_row["expires_at"],
        }


@app.post("/auth/logout")
def auth_logout(payload: TokenRequest, request: Request, response: Response):
    token = _resolve_token(request, payload.token)
    if token:
        with get_auth_conn() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
    _clear_auth_cookie(response)
    return {"success": True, "message": "Logout success"}


@app.get("/auth/config")
def auth_config():
    return {
        "cookie_name": AUTH_COOKIE_NAME,
        "cookie_secure": AUTH_COOKIE_SECURE,
        "cookie_samesite": AUTH_COOKIE_SAMESITE,
        "doctor_self_register_enabled": DOCTOR_SELF_REGISTER_ENABLED,
        "admin_self_register_enabled": DOCTOR_SELF_REGISTER_ENABLED,
    }


def _require_session(request: Request) -> sqlite3.Row:
    token = _resolve_token(request, None)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with get_auth_conn() as conn:
        session_row = get_session(conn, token)
        if not session_row:
            raise HTTPException(status_code=401, detail="Session expired or invalid")
        return session_row


def _require_doctor(request: Request) -> sqlite3.Row:
    session = _require_session(request)
    if not _is_doctor_or_above(session["role"]):
        raise HTTPException(status_code=403, detail="Doctor role required")
    return session


def _require_super_admin(request: Request) -> sqlite3.Row:
    session = _require_session(request)
    if _normalize_role_value(session["role"]) != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super admin role required")
    return session


@app.get("/auth/admin_ping")
def auth_admin_ping(request: Request):
    session = _require_doctor(request)
    return {"success": True, "role": session["role"]}


@app.post("/auth/user_ping")
def auth_user_ping(request: Request):
    _require_session(request)
    return {"success": True}


def _count_super_admins(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(1) FROM users WHERE role = ?",
        (ROLE_SUPER_ADMIN,),
    ).fetchone()
    return int(row[0]) if row else 0


def _invalidate_user_sessions(conn: sqlite3.Connection, user_id: int):
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def _delete_prediction_records_for_user(user_id: int):
    with get_prediction_conn() as conn:
        conn.execute("DELETE FROM bone_age_points WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM predictions WHERE user_id = ?", (user_id,))
        conn.commit()


def _fetch_usernames_by_ids(user_ids: List[int]) -> Dict[int, str]:
    normalized_ids = sorted({int(user_id) for user_id in user_ids})
    if not normalized_ids:
        return {}

    placeholders = ",".join(["?"] * len(normalized_ids))
    with get_auth_conn() as conn:
        rows = conn.execute(
            f"SELECT id, username FROM users WHERE id IN ({placeholders})",
            tuple(normalized_ids),
        ).fetchall()

    return {int(row["id"]): row["username"] for row in rows}


def _fetch_patient_user_or_raise(target_user_id: int) -> sqlite3.Row:
    with get_auth_conn() as conn:
        row = conn.execute(
            "SELECT id, username, role, created_at FROM users WHERE id = ?",
            (target_user_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Target user not found")
    if _normalize_role_value(row["role"]) != ROLE_USER:
        raise HTTPException(status_code=400, detail="Target user must be a personal user")
    return row


@app.get("/auth/users")
def auth_list_users(request: Request):
    _require_super_admin(request)
    with get_auth_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, username, role, created_at
            FROM users
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

    items = sorted(
        [
            {
                "id": int(row["id"]),
                "username": row["username"],
                "role": _normalize_role_value(row["role"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ],
        key=lambda item: (-_role_level(item["role"]), item["created_at"], item["id"]),
    )
    return {"success": True, "items": items}


@app.get("/doctor/patient-users")
def doctor_list_patient_users(request: Request):
    _require_doctor(request)
    with get_auth_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, username, created_at
            FROM users
            WHERE role = ?
            ORDER BY created_at DESC, id DESC
            """,
            (ROLE_USER,),
        ).fetchall()

    return {
        "success": True,
        "items": [
            {
                "id": int(row["id"]),
                "username": row["username"],
                "created_at": row["created_at"],
            }
            for row in rows
        ],
    }


@app.post("/auth/users")
def auth_create_user(payload: AccountCreateRequest, request: Request, response: Response):
    _require_super_admin(request)
    role = _parse_role_or_raise(payload.role, VALID_ROLES)
    username = payload.username.strip()
    if not _validate_username(username):
        raise HTTPException(status_code=400, detail="Username format invalid")
    if not _validate_password_strength(payload.password):
        raise HTTPException(status_code=400, detail="Password must include upper/lower letters and digits, minimum 8 chars")

    salt_hex = secrets.token_hex(16)
    pw_hash = hash_password(payload.password, salt_hex, PBKDF2_ITERATIONS)
    now_iso = _to_iso(_utc_now())

    try:
        with get_auth_conn() as conn:
            conn.execute(
                """
                INSERT INTO users (username, role, password_hash, password_salt, iterations, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username, role, pw_hash, salt_hex, PBKDF2_ITERATIONS, now_iso),
            )
            user_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already exists")

    return {
        "success": True,
        "id": user_id,
        "username": username,
        "role": role,
        "created_at": now_iso,
    }


@app.patch("/auth/users/{target_user_id}/role")
def auth_update_user_role(target_user_id: int, payload: AccountRoleUpdateRequest, request: Request):
    session = _require_super_admin(request)
    new_role = _parse_role_or_raise(payload.role, VALID_ROLES)

    if int(session["user_id"]) == target_user_id:
        raise HTTPException(status_code=400, detail="You cannot change your own role")

    with get_auth_conn() as conn:
        row = conn.execute(
            "SELECT id, username, role FROM users WHERE id = ?",
            (target_user_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        current_role = _normalize_role_value(row["role"])
        if current_role == ROLE_SUPER_ADMIN and new_role != ROLE_SUPER_ADMIN and _count_super_admins(conn) <= 1:
            raise HTTPException(status_code=400, detail="At least one super admin must remain")

        conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, target_user_id))
        _invalidate_user_sessions(conn, target_user_id)
        conn.commit()

    return {"success": True, "id": target_user_id, "role": new_role}


@app.delete("/auth/users/{target_user_id}")
def auth_delete_user(target_user_id: int, request: Request):
    session = _require_super_admin(request)

    if int(session["user_id"]) == target_user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    with get_auth_conn() as conn:
        row = conn.execute(
            "SELECT id, username, role FROM users WHERE id = ?",
            (target_user_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        target_role = _normalize_role_value(row["role"])
        if target_role == ROLE_SUPER_ADMIN and _count_super_admins(conn) <= 1:
            raise HTTPException(status_code=400, detail="At least one super admin must remain")

        _delete_prediction_records_for_user(target_user_id)
        _invalidate_user_sessions(conn, target_user_id)
        conn.execute("DELETE FROM qa_questions WHERE owner_user_id = ?", (target_user_id,))
        conn.execute("DELETE FROM articles WHERE author_id = ?", (target_user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (target_user_id,))
        conn.commit()

    return {"success": True, "id": target_user_id, "username": row["username"]}


class NotificationRequest(BaseModel):
    report_id: str
    method: str  # email, wechat, feishu
    recipient: str  # mail or webhook
    remarks: str = ""
    custom_template: Optional[str] = None
    report_data: Dict[str, Any]

class ArticleCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)

@app.get("/articles")
def list_articles(request: Request):
    session = _require_session(request)
    with get_auth_conn() as conn:
        rows = conn.execute("SELECT id, author_name, title, content, created_at FROM articles ORDER BY id DESC").fetchall()
    return {"success": True, "items": [dict(r) for r in rows]}

@app.post("/articles")
def create_article(payload: ArticleCreateRequest, request: Request):
    session = _require_doctor(request)
    now_iso = _to_iso(_utc_now())
    with get_auth_conn() as conn:
        conn.execute(
            "INSERT INTO articles (author_id, author_name, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], session["username"], payload.title, payload.content, now_iso)
        )
        conn.commit()
    return {"success": True, "message": "Article created"}

class QaCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    image: str = Field(min_length=16, max_length=10_000_000)


class QaReplyRequest(BaseModel):
    reply: str = Field(min_length=1, max_length=10000)


class PredictionUpdateRequest(BaseModel):
    filename: Optional[str] = None
    timestamp: Optional[int] = Field(default=None, ge=0)
    gender: Optional[str] = None
    predicted_age_months: Optional[float] = Field(default=None, ge=0.0)
    predicted_age_years: Optional[float] = Field(default=None, ge=0.0)
    real_age_years: Optional[float] = Field(default=None, ge=0.0)
    predicted_adult_height: Optional[float] = Field(default=None, ge=0.0)


class BoneAgePointCreateRequest(BaseModel):
    user_id: Optional[int] = None
    point_time: Optional[int] = Field(default=None, ge=0)
    bone_age_years: Optional[float] = Field(default=None, ge=0.0, le=30.0)
    chronological_age_years: Optional[float] = Field(default=None, ge=0.0, le=30.0)
    note: str = Field(default="", max_length=500)


class DoctorAssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    prediction_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


def _fetch_prediction_row_for_session(pred_id: str, session: sqlite3.Row) -> sqlite3.Row:
    with get_prediction_conn() as conn:
        row = conn.execute("SELECT * FROM predictions WHERE id = ?", (pred_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if not _is_doctor_or_above(session["role"]) and int(row["user_id"]) != int(session["user_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    return row


def _fit_bone_age_trend(points: List[sqlite3.Row]) -> Dict[str, Any]:
    if len(points) < 2:
        return {
            "enough": False,
            "message": "At least 2 points are required",
            "latex": r"\hat{y}= \beta_0 + \beta_1 t + \beta_2 a",
        }

    base_t = float(points[0]["point_time"])
    x_rows = []
    y_vals = []
    for idx, p in enumerate(points):
        elapsed_years = (float(p["point_time"]) - base_t) / (1000.0 * 60.0 * 60.0 * 24.0 * 365.25)
        chrono = p["chronological_age_years"]
        if chrono is None:
            chrono = elapsed_years
        x_rows.append([1.0, elapsed_years, float(chrono)])
        y_vals.append(float(p["bone_age_years"]))

    x = np.array(x_rows, dtype=np.float64)
    y = np.array(y_vals, dtype=np.float64)
    try:
        coeff, *_ = np.linalg.lstsq(x, y, rcond=None)
        y_hat = x @ coeff
        ss_res = float(np.sum((y - y_hat) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-9 else 1.0
    except np.linalg.LinAlgError:
        return {
            "enough": False,
            "message": "Linear regression failed due to singular matrix",
            "latex": r"\hat{y}= \beta_0 + \beta_1 t + \beta_2 a",
        }

    b0, b1, b2 = coeff.tolist()
    latex = (
        r"\hat{BA}(t,a)="
        + f"{b0:.4f}"
        + (f"{b1:+.4f}" + r"\,t")
        + (f"{b2:+.4f}" + r"\,a")
    )
    return {
        "enough": True,
        "coefficients": {"intercept": round(b0, 6), "time": round(b1, 6), "chronological_age": round(b2, 6)},
        "r2": round(r2, 6),
        "latex": latex,
        "base_timestamp": int(base_t),
    }


@app.get("/qa/questions")
def qa_list_questions(request: Request):
    session = _require_session(request)
    role = session["role"]
    user_id = int(session["user_id"])
    with get_auth_conn() as conn:
        if _is_doctor_or_above(role):
            rows = conn.execute(
                """
                SELECT id, owner_username, question_text, image_base64, reply_text, created_at, updated_at
                FROM qa_questions
                ORDER BY id DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, owner_username, question_text, image_base64, reply_text, created_at, updated_at
                FROM qa_questions
                WHERE owner_user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()

    items = [
        {
            "qid": int(r["id"]),
            "owner": r["owner_username"],
            "text": r["question_text"],
            "image": r["image_base64"],
            "reply": r["reply_text"] or "",
            "createTime": r["created_at"],
            "updateTime": r["updated_at"],
        }
        for r in rows
    ]
    return {"success": True, "items": items}


@app.post("/qa/questions")
def qa_create_question(payload: QaCreateRequest, request: Request):
    session = _require_session(request)
    if session["role"] != "user":
        raise HTTPException(status_code=403, detail="User role required")

    text = payload.text.strip()
    image = payload.image.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Question text cannot be empty")
    if not image.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Invalid image format")

    now_iso = _to_iso(_utc_now())
    with get_auth_conn() as conn:
        conn.execute(
            """
            INSERT INTO qa_questions (owner_user_id, owner_username, question_text, image_base64, reply_text, created_at, updated_at)
            VALUES (?, ?, ?, ?, '', ?, ?)
            """,
            (int(session["user_id"]), session["username"], text, image, now_iso, now_iso),
        )
        qid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()

    return {"success": True, "qid": qid}


@app.post("/qa/questions/{qid}/reply")
def qa_reply_question(qid: int, payload: QaReplyRequest, request: Request):
    _require_doctor(request)
    reply = payload.reply.strip()
    if not reply:
        raise HTTPException(status_code=400, detail="Reply cannot be empty")

    now_iso = _to_iso(_utc_now())
    with get_auth_conn() as conn:
        cur = conn.execute(
            "UPDATE qa_questions SET reply_text = ?, updated_at = ? WHERE id = ?",
            (reply, now_iso, qid),
        )
        conn.commit()
        if cur.rowcount <= 0:
            raise HTTPException(status_code=404, detail="Question not found")
    return {"success": True}


@app.delete("/qa/questions/{qid}")
def qa_delete_question(qid: int, request: Request):
    session = _require_session(request)
    role = session["role"]
    user_id = int(session["user_id"])
    with get_auth_conn() as conn:
        if _is_doctor_or_above(role):
            cur = conn.execute("DELETE FROM qa_questions WHERE id = ?", (qid,))
        else:
            cur = conn.execute(
                "DELETE FROM qa_questions WHERE id = ? AND owner_user_id = ?",
                (qid, user_id),
            )
        conn.commit()
        if cur.rowcount <= 0:
            raise HTTPException(status_code=404, detail="Question not found")
    return {"success": True}


@app.delete("/qa/questions")
def qa_clear_questions(request: Request):
    session = _require_session(request)
    role = session["role"]
    user_id = int(session["user_id"])
    with get_auth_conn() as conn:
        if _is_doctor_or_above(role):
            cur = conn.execute("DELETE FROM qa_questions")
        else:
            cur = conn.execute("DELETE FROM qa_questions WHERE owner_user_id = ?", (user_id,))
        conn.commit()
    return {"success": True, "deleted": int(cur.rowcount)}


@app.post("/send_notification")
async def send_notification(request: NotificationRequest):
    method = request.method.lower()
    try:
        if method == "email":
            return await NotificationService.send_email(
                recipient=request.recipient,
                report_data=request.report_data,
                remarks=request.remarks,
                custom_template=request.custom_template,
                report_id=request.report_id,
            )
        if method == "wechat":
            return await NotificationService.send_wechat_webhook(
                webhook_url=request.recipient,
                report_data=request.report_data,
                remarks=request.remarks,
                custom_template=request.custom_template,
                report_id=request.report_id,
            )
        if method == "feishu":
            return await NotificationService.send_feishu_webhook(
                webhook_url=request.recipient,
                report_data=request.report_data,
                remarks=request.remarks,
                custom_template=request.custom_template,
                report_id=request.report_id,
            )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported method: {request.method}. Supported: email, wechat, feishu",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Notification failed: {exc}")


@app.post("/predict")
async def predict_bone_age(
    request: Request,
    file: UploadFile = File(...),
    gender: str = Form(..., description="Gender: 'male' or 'female'"),
    height: Optional[float] = Form(None, description="Current height in cm"),
    real_age_years: Optional[float] = Form(None, description="Chronological age in years"),
    target_user_id: Optional[int] = Form(default=None, description="Personal user id for doctor-created predictions"),
    preprocessing_enabled: bool = Form(False),
    brightness: float = Form(0.0),
    contrast: float = Form(1.0),
):
    if not models_ensemble:
        raise HTTPException(status_code=503, detail="Age model not loaded")

    gender_lower = gender.lower()
    if gender_lower not in ["male", "female"]:
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

    token = _resolve_token(request, None)
    session_row = None
    if token:
        with get_auth_conn() as conn:
            session_row = get_session(conn, token)

    target_user_row = None
    if target_user_id is not None:
        if not session_row:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if not _is_doctor_or_above(session_row["role"]):
            raise HTTPException(status_code=403, detail="Doctor role required")
        target_user_row = _fetch_patient_user_or_raise(int(target_user_id))

    owner_user_id = (
        int(target_user_row["id"])
        if target_user_row
        else (int(session_row["user_id"]) if session_row else None)
    )
    owner_username = (
        target_user_row["username"]
        if target_user_row
        else (session_row["username"] if session_row else None)
    )

    gender_val = 1.0 if gender_lower == "male" else 0.0
    gender_tensor = torch.tensor([[gender_val]], dtype=torch.float32, device=device)

    try:
        content = await file.read()

        anomalies = []
        detection_image_base64 = None
        if fracture_detector:
            try:
                anomalies, detection_image_base64 = fracture_detector.detect(
                    content,
                    score_threshold=ANOMALY_SCORE_THRESHOLD,
                )
            except Exception as det_exc:
                print(f"Fracture detect failed: {det_exc}")

        foreign_object_detection = build_foreign_object_detection(anomalies)

        recognized_joints_13 = {
            "hand_side": "unknown",
            "detected_count": 0,
            "joints": {},
            "plot_image_base64": None,
        }
        if joint_recognizer:
            try:
                recognized_joints_13 = joint_recognizer.recognize_13(content)
            except Exception as rec_exc:
                print(f"Small joint recognize failed: {rec_exc}")

        joint_grades = {}
        if joint_grader:
            try:
                joint_grades = joint_grader.predict_detected_joints(
                    content,
                    recognized_joints_13.get("joints", {}),
                    JOINT_IMG_SIZE,
                    IMAGENET_MEAN,
                    IMAGENET_STD,
                )
            except Exception as joint_exc:
                print(f"Joint grading failed: {joint_exc}")
        joint_grades = semantic_align_missing_joint_grades(joint_grades)

        joint_semantic_13 = {}
        joint_rus_total_score = None
        joint_rus_details = []
        if joint_grades:
            joint_semantic_13 = align_joint_semantics(joint_grades)
            joint_rus_total_score, joint_rus_details = calc_rus_score(joint_semantic_13, gender_lower)

        # 决定是否使用预处理参数
        if preprocessing_enabled:
            img_tensor = preprocess_image(content, brightness=brightness, contrast=contrast).to(device)
        else:
            img_tensor = preprocess_image(content).to(device)
        
        pred_months = predict_with_ensemble_tta_months(img_tensor, gender_tensor)
        pred_years = pred_months / 12.0

        report_details = generate_bone_report(pred_years, gender_lower)
        predicted_adult_height = (
            predict_adult_height(height, pred_years, gender_lower) if height else None
        )

        heatmap_base64 = build_gradcam_heatmap(img_tensor, gender_tensor)

        result_payload = {
            "filename": file.filename,
            "predicted_age_months": round(pred_months, 2),
            "predicted_age_years": round(pred_years, 2),
            "gender": gender_lower,
            "real_age_years": real_age_years,
            "anomalies": anomalies,
            "foreign_object_detection": foreign_object_detection,
            "detection_image_base64": detection_image_base64,
            "joint_grades": joint_grades,
            "joint_semantic_13": joint_semantic_13,
            "joint_rus_total_score": joint_rus_total_score,
            "joint_rus_details": joint_rus_details,
            "joint_detect_13": recognized_joints_13,
            "rus_chn_details": report_details,
            "heatmap_base64": heatmap_base64,
            "predicted_adult_height": predicted_adult_height,
            "ensemble_size": len(models_ensemble),
        }
        if owner_user_id is not None:
            result_payload["user_id"] = owner_user_id
        if owner_username:
            result_payload["username"] = owner_username

        # Save to database if session exists
        if owner_user_id is not None:

            pred_id = str(uuid.uuid4())
            now_ts = int(time.time() * 1000)

            # Ensure the stored JSON contains id and timestamp so full_json
            # stays consistent with the other table columns.
            result_payload["id"] = pred_id
            result_payload["timestamp"] = now_ts

            with get_prediction_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO predictions (id, user_id, timestamp, filename, predicted_age_months, predicted_age_years, gender, real_age_years, predicted_adult_height, full_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pred_id,
                        owner_user_id,
                        now_ts,
                        file.filename or "unknown.jpg",
                        result_payload["predicted_age_months"],
                        result_payload["predicted_age_years"],
                        gender_lower,
                        real_age_years,
                        predicted_adult_height,
                        json.dumps(result_payload),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO bone_age_points (user_id, point_time, bone_age_years, chronological_age_years, source, prediction_id, note, created_at)
                    VALUES (?, ?, ?, ?, 'prediction', ?, '', ?)
                    """,
                    (
                        owner_user_id,
                        now_ts,
                        result_payload["predicted_age_years"],
                        real_age_years,
                        pred_id,
                        _to_iso(_utc_now()),
                    ),
                )
                conn.commit()
            # `result_payload` already contains `id` and `timestamp`.

        return result_payload

    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

@app.get("/predictions")
def list_predictions(request: Request):
    session = _require_session(request)
    user_id = int(session["user_id"])
    role = str(session["role"])

    with get_prediction_conn() as conn:
        if _is_doctor_or_above(role):
            rows = conn.execute("SELECT id, user_id, timestamp, filename, predicted_age_years, gender FROM predictions ORDER BY timestamp DESC LIMIT 100").fetchall()
        else:
            rows = conn.execute("SELECT id, timestamp, filename, predicted_age_years, gender FROM predictions WHERE user_id = ? ORDER BY timestamp DESC", (user_id,)).fetchall()
    items = [{k: r[k] for k in r.keys()} for r in rows]
    if _is_doctor_or_above(role):
        usernames = _fetch_usernames_by_ids([int(item["user_id"]) for item in items if item.get("user_id") is not None])
        for item in items:
            item["username"] = usernames.get(int(item["user_id"]), "")

    return {"success": True, "items": items}


@app.get("/predictions/{pred_id}")
def get_prediction_detail(pred_id: str, request: Request):
    session = _require_session(request)
    row = _fetch_prediction_row_for_session(pred_id, session)

    data = json.loads(row["full_json"])
    data["id"] = pred_id
    data["timestamp"] = row["timestamp"]
    data["real_age_years"] = row["real_age_years"]
    data["user_id"] = int(row["user_id"])
    data["foreign_object_detection"] = build_foreign_object_detection(data.get("anomalies"))
    usernames = _fetch_usernames_by_ids([int(row["user_id"])])
    if usernames.get(int(row["user_id"])):
        data["username"] = usernames[int(row["user_id"])]
    return {"success": True, "data": data}


@app.put("/predictions/{pred_id}")
def update_prediction(pred_id: str, payload: PredictionUpdateRequest, request: Request):
    session = _require_session(request)
    row = _fetch_prediction_row_for_session(pred_id, session)

    full_json = json.loads(row["full_json"])
    update_fields = {
        "filename": payload.filename,
        "timestamp": payload.timestamp,
        "gender": payload.gender.lower().strip() if payload.gender else None,
        "predicted_age_months": payload.predicted_age_months,
        "predicted_age_years": payload.predicted_age_years,
        "real_age_years": payload.real_age_years,
        "predicted_adult_height": payload.predicted_adult_height,
    }

    if update_fields["gender"] and update_fields["gender"] not in {"male", "female"}:
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

    if update_fields["predicted_age_years"] is not None and update_fields["predicted_age_months"] is None:
        update_fields["predicted_age_months"] = float(update_fields["predicted_age_years"]) * 12.0

    for key, val in update_fields.items():
        if val is not None:
            full_json[key] = val
    full_json["foreign_object_detection"] = build_foreign_object_detection(full_json.get("anomalies"))

    new_filename = update_fields["filename"] if update_fields["filename"] is not None else row["filename"]
    new_timestamp = int(update_fields["timestamp"]) if update_fields["timestamp"] is not None else int(row["timestamp"])
    new_gender = update_fields["gender"] if update_fields["gender"] is not None else row["gender"]
    new_months = float(update_fields["predicted_age_months"]) if update_fields["predicted_age_months"] is not None else float(row["predicted_age_months"])
    new_years = float(update_fields["predicted_age_years"]) if update_fields["predicted_age_years"] is not None else float(row["predicted_age_years"])
    new_real_age = update_fields["real_age_years"] if update_fields["real_age_years"] is not None else row["real_age_years"]
    new_height = (
        update_fields["predicted_adult_height"]
        if update_fields["predicted_adult_height"] is not None
        else row["predicted_adult_height"]
    )

    with get_prediction_conn() as conn:
        conn.execute(
            """
            UPDATE predictions
            SET filename = ?, timestamp = ?, predicted_age_months = ?, predicted_age_years = ?, gender = ?, real_age_years = ?, predicted_adult_height = ?, full_json = ?
            WHERE id = ?
            """,
            (new_filename, new_timestamp, new_months, new_years, new_gender, new_real_age, new_height, json.dumps(full_json), pred_id),
        )
        if update_fields["predicted_age_years"] is not None or update_fields["real_age_years"] is not None or update_fields["timestamp"] is not None:
            conn.execute(
                """
                UPDATE bone_age_points
                SET point_time = ?, bone_age_years = ?, chronological_age_years = ?
                WHERE prediction_id = ?
                """,
                (new_timestamp, new_years, new_real_age, pred_id),
            )
        conn.commit()

    return {"success": True, "message": "Prediction updated"}


@app.delete("/predictions/{pred_id}")
def delete_prediction(pred_id: str, request: Request):
    session = _require_session(request)
    row = _fetch_prediction_row_for_session(pred_id, session)

    with get_prediction_conn() as conn:
        conn.execute("DELETE FROM bone_age_points WHERE prediction_id = ?", (pred_id,))
        conn.execute("DELETE FROM predictions WHERE id = ?", (pred_id,))
        conn.commit()

    return {"success": True, "id": pred_id, "user_id": int(row["user_id"])}


@app.get("/bone-age-points")
def list_bone_age_points(request: Request, user_id: Optional[int] = Query(default=None)):
    session = _require_session(request)
    uid = int(session["user_id"])
    role = str(session["role"])
    target_user_id = user_id if (_is_doctor_or_above(role) and user_id is not None) else uid

    with get_prediction_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, point_time, bone_age_years, chronological_age_years, source, prediction_id, note, created_at
            FROM bone_age_points
            WHERE user_id = ?
            ORDER BY point_time ASC, id ASC
            """,
            (target_user_id,),
        ).fetchall()

    return {"success": True, "items": [{k: r[k] for k in r.keys()} for r in rows]}


@app.post("/bone-age-points")
async def create_bone_age_point(request: Request):
    session = _require_session(request)
    uid = int(session["user_id"])
    role = str(session["role"])

    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError("payload must be object")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    raw_user_id = payload.get("user_id")
    raw_point_time = payload.get("point_time")
    raw_bone_age_years = payload.get("bone_age_years")
    raw_chronological_age_years = payload.get("chronological_age_years")
    raw_note = payload.get("note", "")

    def _to_optional_float(v):
        if v is None or v == "":
            return None
        try:
            f = float(v)
        except Exception:
            return None
        if np.isnan(f) or np.isinf(f):
            return None
        return f

    def _to_optional_int(v):
        if v is None or v == "":
            return None
        try:
            return int(v)
        except Exception:
            return None

    bone_age_years = _to_optional_float(raw_bone_age_years)
    if bone_age_years is None or bone_age_years <= 0:
        raise HTTPException(status_code=400, detail="bone_age_years must be a valid number > 0")
    if bone_age_years > 30:
        raise HTTPException(status_code=400, detail="bone_age_years must be <= 30")

    chronological_age_years = _to_optional_float(raw_chronological_age_years)
    if chronological_age_years is not None and chronological_age_years > 30:
        raise HTTPException(status_code=400, detail="chronological_age_years must be <= 30")

    parsed_user_id = _to_optional_int(raw_user_id)
    parsed_point_time = _to_optional_int(raw_point_time)
    note = str(raw_note or "").strip()[:500]

    target_user_id = parsed_user_id if (_is_doctor_or_above(role) and parsed_user_id is not None) else uid
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    point_time = parsed_point_time if parsed_point_time is not None else now_ts
    now_iso = _to_iso(_utc_now())

    with get_prediction_conn() as conn:
        conn.execute(
            """
            INSERT INTO bone_age_points (user_id, point_time, bone_age_years, chronological_age_years, source, prediction_id, note, created_at)
            VALUES (?, ?, ?, ?, 'manual', NULL, ?, ?)
            """,
            (target_user_id, point_time, bone_age_years, chronological_age_years, note, now_iso),
        )
        point_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()

    return {"success": True, "id": point_id}


@app.delete("/bone-age-points/{point_id}")
def delete_bone_age_point(point_id: int, request: Request):
    session = _require_session(request)
    uid = int(session["user_id"])
    role = str(session["role"])

    with get_prediction_conn() as conn:
        row = conn.execute("SELECT user_id FROM bone_age_points WHERE id = ?", (point_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Point not found")
        if not _is_doctor_or_above(role) and int(row["user_id"]) != uid:
            raise HTTPException(status_code=403, detail="Access denied")
        conn.execute("DELETE FROM bone_age_points WHERE id = ?", (point_id,))
        conn.commit()

    return {"success": True}


@app.get("/bone-age-trend")
def get_bone_age_trend(request: Request, user_id: Optional[int] = Query(default=None)):
    session = _require_session(request)
    uid = int(session["user_id"])
    role = str(session["role"])
    target_user_id = user_id if (_is_doctor_or_above(role) and user_id is not None) else uid

    with get_prediction_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, point_time, bone_age_years, chronological_age_years
            FROM bone_age_points
            WHERE user_id = ?
            ORDER BY point_time ASC, id ASC
            """,
            (target_user_id,),
        ).fetchall()

    trend = _fit_bone_age_trend(rows)
    return {"success": True, "points": len(rows), **trend}


@app.post("/doctor/ai-assistant")
async def doctor_ai_assistant(payload: DoctorAssistantRequest, request: Request):
    _require_doctor(request)
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail="DEEPSEEK_API_KEY is not configured")

    context_chunks: List[str] = []
    if payload.context:
        context_chunks.append(f"额外上下文: {payload.context}")
    if payload.prediction_id:
        with get_prediction_conn() as conn:
            row = conn.execute("SELECT full_json FROM predictions WHERE id = ?", (payload.prediction_id,)).fetchone()
        if row:
            context_chunks.append(f"预测记录[{payload.prediction_id}]: {row['full_json'][:4000]}")

    system_prompt = (
        "你是骨龄辅助诊断AI，请输出临床可用、谨慎、结构化建议。"
        "请明确说明不确定性，不可替代医生最终判断。"
    )
    user_prompt = payload.message.strip()
    if context_chunks:
        user_prompt = user_prompt + "\n\n" + "\n".join(context_chunks)

    api_url = DEEPSEEK_API_BASE.rstrip("/") + "/chat/completions"

    async def generate_stream():
        try:
            resp = requests.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                    "stream": True,
                },
                timeout=60,
                stream=True,
            )
            if not resp.ok:
                yield f"data: {json.dumps({'error': f'DeepSeek API error: {resp.text[:400]}'})}\n\n"
                return

            for line in resp.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]
                        if data_str == '[DONE]':
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get('choices', [])
                            if not choices:
                                continue
                            delta = choices[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            yield f"data: {json.dumps({'error': f'AI assistant failed: {exc}'})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


class UserConsultRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@app.post("/user/ai-consult")
async def user_ai_consult(payload: UserConsultRequest, request: Request):
    """患者智能问诊接口：任意已登录用户均可调用，prompt 偏向健康科普与就医指导。"""
    _require_session(request)
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail="智能问诊服务暂未开放，请联系管理员配置 API 密钥")

    system_prompt = (
        "你是一位友好、专业的骨龄与儿童生长发育健康顾问。"
        "你的角色是向患者及家长提供通俗易懂的健康科普解释，帮助他们理解骨龄概念、发育规律以及相关注意事项。"
        "请用温和、清晰、易理解的语言回答，避免使用晦涩的专业术语。"
        "对于需要临床检查或诊断的问题，请明确建议用户就诊，不替代医生专业判断。"
        "回答时请结构清晰，必要时使用条目列表。"
    )

    api_url = DEEPSEEK_API_BASE.rstrip("/") + "/chat/completions"

    async def generate_stream():
        try:
            resp = requests.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": payload.message.strip()},
                    ],
                    "temperature": 0.4,
                    "stream": True,
                },
                timeout=60,
                stream=True,
            )
            if not resp.ok:
                yield f"data: {json.dumps({'error': f'AI 服务调用失败: {resp.text[:400]}'})}\n\n"
                return

            for line in resp.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]
                        if data_str == '[DONE]':
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get('choices', [])
                            if not choices:
                                continue
                            delta = choices[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            yield f"data: {json.dumps({'error': f'智能问诊失败: {exc}'})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


class ImageConsultRequest(BaseModel):
    message: str = Field(default="", max_length=2000)
    image_base64: str = Field(..., description="Base64 encoded image data")


@app.post("/user/ai-consult-image")
async def user_ai_consult_with_image(payload: ImageConsultRequest, request: Request):
    """患者智能问诊接口（支持图片）：用户可上传X光片等图片进行问诊"""
    _require_session(request)
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail="智能问诊服务暂未开放，请联系管理员配置 API 密钥")

    system_prompt = (
        "你是一位友好、专业的骨龄与儿童生长发育健康顾问。"
        "你的角色是向患者及家长提供通俗易懂的健康科普解释，帮助他们理解骨龄概念、发育规律以及相关注意事项。"
        "请用温和、清晰、易理解的语言回答，避免使用晦涩的专业术语。"
        "对于需要临床检查或诊断的问题，请明确建议用户就诊，不替代医生专业判断。"
        "回答时请结构清晰，必要时使用条目列表。"
        "如果用户上传了X光片图片，请仔细观察并给出专业的解读建议。"
    )

    api_url = DEEPSEEK_API_BASE.rstrip("/") + "/chat/completions"

    user_content = []
    if payload.message.strip():
        user_content.append({"type": "text", "text": payload.message.strip()})
    else:
        user_content.append({"type": "text", "text": "请帮我分析这张图片"})

    if payload.image_base64:
        image_data = payload.image_base64
        if not image_data.startswith('data:'):
            image_data = f"data:image/jpeg;base64,{image_data}"
        user_content.append({
            "type": "image_url",
            "image_url": {"url": image_data}
        })

    async def generate_stream():
        try:
            resp = requests.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.4,
                    "stream": True,
                },
                timeout=120,
                stream=True,
            )
            if not resp.ok:
                yield f"data: {json.dumps({'error': f'AI 服务调用失败: {resp.text[:400]}'})}\n\n"
                return

            for line in resp.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]
                        if data_str == '[DONE]':
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get('choices', [])
                            if not choices:
                                continue
                            delta = choices[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            yield f"data: {json.dumps({'error': f'智能问诊失败: {exc}'})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


# @app.post("/joint-grading")

# async def joint_grading_predict(
#     file: UploadFile = File(...),
#     gender: str = Form(..., description="Gender: 'male' or 'female'"),
# ):
#     """小关节分级独立接口：仅进行13个小关节的检测与分级"""
#     if not joint_recognizer:
#         raise HTTPException(status_code=503, detail="小关节检测模型未加载")
#     if not joint_grader:
#         raise HTTPException(status_code=503, detail="小关节分级模型未加载")

#     gender_lower = gender.lower()
#     if gender_lower not in ["male", "female"]:
#         raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

#     try:
#         content = await file.read()

#         recognized_joints_13 = {}
#         try:
#             recognized_joints_13 = joint_recognizer.recognize_13(content)
#         except Exception as rec_exc:
#             print(f"Small joint recognize failed: {rec_exc}")
@app.post("/joint-grading")

async def joint_grading_predict(
    file: UploadFile = File(...),
    gender: str = Form(..., description="Gender: 'male' or 'female'"),
    preprocessing_enabled: bool = Form(False),
    brightness: float = Form(0.0),
    contrast: float = Form(1.0),
    use_dpv3: bool = Form(False, description="是否使用DP V3增强检测"),
):
    """小关节分级独立接口：仅进行13个小关节的检测与分级"""
    if not joint_grader:
        raise HTTPException(status_code=503, detail="小关节分级模型未加载")

    gender_lower = gender.lower()
    if gender_lower not in ["male", "female"]:
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

    try:
        content = await file.read()
        validate_image_content(content)

        if preprocessing_enabled:
            try:
                processed_content = preprocess_image_bytes(content, brightness=brightness, contrast=contrast)
            except Exception:
                processed_content = content
        else:
            processed_content = content
        with open("check_this_image.jpg", "wb") as f:
            f.write(processed_content)

        recognized_joints_13 = {
            "hand_side": "unknown",
            "detected_count": 0,
            "joints": {},
            "plot_image_base64": None,
            "dpv3_enhanced": False,
            "dpv3_info": None
        }

        if use_dpv3 and dpv3_detector:
            try:
                nparr = np.frombuffer(processed_content, np.uint8)
                img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img_bgr is not None:
                    dpv3_results = dpv3_detector.detect(img_bgr, target_count=21)
                    if dpv3_results.get('success'):
                        recognized_joints_13["dpv3_enhanced"] = True

                        radius_region = None
                        ulna_region = None
                        for region in dpv3_results.get('regions', []):
                            label = region.get('label', 'Unknown')
                            if label == 'Radius':
                                radius_region = region
                            elif label == 'Ulna':
                                ulna_region = region

                        if radius_region and ulna_region:
                            radius_x = radius_region.get('centroid', (0, 0))[0]
                            ulna_x = ulna_region.get('centroid', (0, 0))[0]
                            if radius_x > ulna_x:
                                hand_side = 'left'
                            else:
                                hand_side = 'right'
                        else:
                            hand_side = dpv3_results.get('hand_side', 'unknown')

                        recognized_joints_13["dpv3_info"] = {
                            "hand_side": hand_side,
                            "total_regions": dpv3_results.get('total_regions'),
                            "yolo_count": dpv3_results.get('yolo_count'),
                            "bfs_count": dpv3_results.get('bfs_count'),
                            "best_gray_range": dpv3_results.get('best_gray_range'),
                            "merged_blocks": dpv3_results.get('merged_blocks')
                        }

                        finger_labels_en = ['First', 'Second', 'Third', 'Fourth', 'Fifth']
                        finger_labels_cn = ['拇指', '食指', '中指', '环指', '小指']

                        if hand_side == 'left':
                            finger_order = finger_labels_en
                        else:
                            finger_order = list(reversed(finger_labels_en))

                        finger_regions_map = {f: [] for f in finger_labels_en}
                        finger_cn_map = dict(zip(finger_labels_en, finger_labels_cn))
                        carpal_regions = []

                        thumb_regions = []
                        other_regions = []

                        for region in dpv3_results.get('regions', []):
                            label = region.get('label', 'Unknown')
                            if label in ['Radius', 'Ulna']:
                                carpal_regions.append(region)
                            elif label == 'MCPFirst':
                                thumb_regions.append(region)
                            elif label in ['ProximalPhalanx', 'MCP', 'MiddlePhalanx', 'DistalPhalanx']:
                                other_regions.append(region)

                        if not thumb_regions and other_regions:
                            img_width = img_bgr.shape[1]
                            thumb_threshold = img_width * 0.85 if hand_side == 'left' else img_width * 0.15
                            if hand_side == 'left':
                                thumb_regions = [r for r in other_regions if r.get('centroid', (0, 0))[0] > thumb_threshold]
                            else:
                                thumb_regions = [r for r in other_regions if r.get('centroid', (0, 0))[0] < thumb_threshold]
                            other_regions = [r for r in other_regions if r not in thumb_regions]

                        finger_regions_map['First'].extend(thumb_regions)

                        if other_regions:
                            sorted_by_x = sorted(other_regions, key=lambda r: r.get('centroid', (0, 0))[0])

                            if hand_side == 'left':
                                sorted_by_x.reverse()

                            step = len(sorted_by_x) / 4
                            other_finger_labels = ['Second', 'Third', 'Fourth', 'Fifth']
                            for i, finger in enumerate(other_finger_labels):
                                start_idx = int(i * step)
                                end_idx = int((i + 1) * step) if i < 3 else len(sorted_by_x)
                                finger_regions_map[finger].extend(sorted_by_x[start_idx:end_idx])

                        joints = {}
                        ordered_joints = []
                        joint_index = 0

                        label_counter = {f: {} for f in finger_order}

                        for finger in finger_order:
                            finger_regions = finger_regions_map[finger]
                            if not finger_regions:
                                continue

                            sorted_regions = sorted(
                                finger_regions,
                                key=lambda r: (r.get('centroid', (0, 0))[1], r.get('centroid', (0, 0))[0])
                            )

                            for region in sorted_regions:
                                label = region.get('label', 'Unknown')
                                label_cn = region.get('label_cn', label)
                                bbox_coords = region.get('bbox_coords', [0, 0, 0, 0])
                                x1, y1, x2, y2 = bbox_coords

                                if label == 'MCPFirst':
                                    grade_label = 'MCPFirst'
                                elif label == 'ProximalPhalanx':
                                    grade_label = f'PIP{finger}'
                                elif label == 'DistalPhalanx':
                                    grade_label = f'DIP{finger}'
                                elif label == 'MiddlePhalanx':
                                    grade_label = f'MIP{finger}'
                                elif label == 'MCP':
                                    grade_label = f'MCP{finger}'
                                else:
                                    grade_label = label

                                joint_data = {
                                    "type": label_cn,
                                    "label": grade_label,
                                    "yolo_label": label,
                                    "finger": finger,
                                    "finger_cn": finger_cn_map[finger],
                                    "order": joint_index,
                                    "score": round(region.get('confidence', 0.5), 4),
                                    "bbox_xyxy": [round(float(x1), 2), round(float(y1), 2), round(float(x2), 2), round(float(y2), 2)],
                                    "source": region.get('source', 'unknown'),
                                    "coord": [
                                        round(region['centroid'][0] / img_bgr.shape[1], 4),
                                        round(region['centroid'][1] / img_bgr.shape[0], 4),
                                        round((x2 - x1) / img_bgr.shape[1], 4),
                                        round((y2 - y1) / img_bgr.shape[0], 4)
                                    ]
                                }

                                if grade_label in joints:
                                    idx = 1
                                    while f"{grade_label}_{idx}" in joints:
                                        idx += 1
                                    joint_key = f"{grade_label}_{idx}"
                                else:
                                    joint_key = grade_label

                                joints[joint_key] = joint_data
                                ordered_joints.append(joint_data)
                                joint_index += 1

                        if carpal_regions:
                            sorted_carpal = sorted(
                                carpal_regions,
                                key=lambda r: r.get('centroid', (0, 0))[1]
                            )

                            for region in sorted_carpal:
                                label = region.get('label', 'Unknown')
                                label_cn = region.get('label_cn', label)
                                bbox_coords = region.get('bbox_coords', [0, 0, 0, 0])
                                x1, y1, x2, y2 = bbox_coords

                                joint_data = {
                                    "type": label_cn,
                                    "label": label,
                                    "finger": 'Wrist',
                                    "finger_cn": '腕骨',
                                    "order": joint_index,
                                    "score": round(region.get('confidence', 0.5), 4),
                                    "bbox_xyxy": [round(float(x1), 2), round(float(y1), 2), round(float(x2), 2), round(float(y2), 2)],
                                    "source": region.get('source', 'unknown'),
                                    "coord": [
                                        round(region['centroid'][0] / img_bgr.shape[1], 4),
                                        round(region['centroid'][1] / img_bgr.shape[0], 4),
                                        round((x2 - x1) / img_bgr.shape[1], 4),
                                        round((y2 - y1) / img_bgr.shape[0], 4)
                                    ]
                                }

                                if label in joints:
                                    idx = 1
                                    while f"{label}_{idx}" in joints:
                                        idx += 1
                                    joint_key = f"{label}_{idx}"
                                else:
                                    joint_key = label

                                joints[joint_key] = joint_data
                                ordered_joints.append(joint_data)
                                joint_index += 1

                        recognized_joints_13["detected_count"] = len(joints)
                        recognized_joints_13["hand_side"] = hand_side
                        recognized_joints_13["joints"] = joints
                        recognized_joints_13["ordered_joints"] = ordered_joints
                        recognized_joints_13["finger_order"] = finger_order
                        print(f"✅ DP V3 enhanced detection: {recognized_joints_13['detected_count']} bones detected")
            except Exception as dpv3_exc:
                print(f"DP V3 detection failed: {dpv3_exc}")
                import traceback
                traceback.print_exc()

        if not recognized_joints_13.get("dpv3_enhanced"):
            joints = {}
            if joint_recognizer:
                try:
                    recognized_joints_13 = joint_recognizer.recognize_13(processed_content)
                    recognized_joints_13["dpv3_enhanced"] = False
                    recognized_joints_13["dpv3_info"] = None
                except Exception as rec_exc:
                    print(f"Small joint recognize failed: {rec_exc}")
            joints = recognized_joints_13.get("joints", {})

        joint_grades = {}
        try:
            joint_grades = joint_grader.predict_detected_joints(
                processed_content,
                recognized_joints_13.get("joints", {}),
                JOINT_IMG_SIZE,
                IMAGENET_MEAN,
                IMAGENET_STD,
            )
        except Exception as joint_exc:
            print(f"Joint grading failed: {joint_exc}")

        joint_grades = semantic_align_missing_joint_grades(joint_grades)

        joint_semantic_13 = {}
        joint_rus_total_score = 0.0
        joint_rus_details = []
        if joint_grades:
            joint_semantic_13 = align_joint_semantics(joint_grades)
            joint_rus_total_score, joint_rus_details = calc_rus_score(joint_semantic_13, gender_lower)
            if joint_rus_total_score is not None and (math.isnan(joint_rus_total_score) or math.isinf(joint_rus_total_score)):
                joint_rus_total_score = 0.0

        if joint_recognizer and joint_grades:
            try:
                nparr = np.frombuffer(processed_content, np.uint8)
                img_bgr_orig = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                orig_h, orig_w = img_bgr_orig.shape[:2]

                img_bgr = cv2.resize(img_bgr_orig, (joint_recognizer.imgsz, joint_recognizer.imgsz))
                scale_x = joint_recognizer.imgsz / orig_w
                scale_y = joint_recognizer.imgsz / orig_h

                scaled_joints = {}
                for joint_key, joint_data in recognized_joints_13.get("joints", {}).items():
                    bbox = joint_data.get("bbox_xyxy", [0, 0, 0, 0])
                    x1, y1, x2, y2 = bbox
                    scaled_joints[joint_key] = {
                        **joint_data,
                        "bbox_xyxy": [
                            x1 * scale_x,
                            y1 * scale_y,
                            x2 * scale_x,
                            y2 * scale_y
                        ]
                    }

                new_plot = joint_recognizer._render_with_plt(
                    img_bgr,
                    scaled_joints,
                    recognized_joints_13.get("hand_side", "unknown"),
                    grades=joint_grades
                )
                if new_plot:
                    recognized_joints_13["plot_image_base64"] = new_plot
            except Exception as plot_exc:
                print(f"Re-rendering plot with grades failed: {plot_exc}")
                import traceback
                traceback.print_exc()

        return {
            "success": True,
            "filename": file.filename,
            "gender": gender_lower,
            "joint_detect_13": recognized_joints_13,
            "joint_grades": joint_grades,
            "joint_semantic_13": joint_semantic_13,
            "joint_rus_total_score": joint_rus_total_score,
            "joint_rus_details": joint_rus_details,
            "detection_algorithm": "dpv3" if recognized_joints_13.get("dpv3_enhanced") else "yolo"
        }
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"小关节分级诊断失败: {exc}")


@app.post("/joint-dpv3-detect")
async def joint_dpv3_detect(
    file: UploadFile = File(...),
    gender: str = Form(..., description="Gender: 'male' or 'female'"),
    preprocessing_enabled: bool = Form(False),
    brightness: float = Form(0.0),
    contrast: float = Form(1.0),
):
    """
    DP V3增强小关节检测接口：使用DP灰度扩展算法补充检测腕骨等YOLO未检测到的骨骼

    特点：
    1. YOLO检测21个标准骨骼
    2. 创建YOLO遮罩排除已检测区域
    3. BFS聚类分块（仅非遮罩区域）
    4. Union-Find去重合并重叠分块
    5. DP灰度扩展: YOLO(21) + BFS补充 = 23个骨骼
    """
    if not dpv3_detector:
        raise HTTPException(status_code=503, detail="DP V3检测器未加载，请检查模型文件")

    if not joint_grader:
        raise HTTPException(status_code=503, detail="小关节分级模型未加载")

    gender_lower = gender.lower()
    if gender_lower not in ["male", "female"]:
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

    try:
        content = await file.read()
        validate_image_content(content)

        if preprocessing_enabled:
            try:
                processed_content = preprocess_image_bytes(content, brightness=brightness, contrast=contrast)
            except Exception:
                processed_content = content
        else:
            processed_content = content

        nparr = np.frombuffer(processed_content, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise HTTPException(status_code=400, detail="无法解码图像")

        dpv3_results = dpv3_detector.detect(img_bgr, target_count=21)

        detected_joints = {}
        if dpv3_results.get('success'):
            h, w = img_bgr.shape[:2]
            for region in dpv3_results.get('regions', []):
                label = region.get('label', 'Unknown')
                label_cn = region.get('label_cn', label)
                bbox_coords = region.get('bbox_coords', [0, 0, 0, 0])

                detected_joints[label_cn] = {
                    "type": label_cn,
                    "score": region.get('confidence', 0.5),
                    "bbox_xyxy": list(bbox_coords),
                    "source": region.get('source', 'unknown'),
                    "coord": [
                        region['centroid'][0] / w,
                        region['centroid'][1] / h,
                        (bbox_coords[2] - bbox_coords[0]) / w,
                        (bbox_coords[3] - bbox_coords[1]) / h
                    ]
                }

        joint_grades = {}
        try:
            joint_grades = joint_grader.predict_detected_joints(
                processed_content,
                detected_joints,
                JOINT_IMG_SIZE,
                IMAGENET_MEAN,
                IMAGENET_STD,
            )
        except Exception as joint_exc:
            print(f"Joint grading failed: {joint_exc}")

        joint_grades = semantic_align_missing_joint_grades(joint_grades)

        joint_semantic_13 = {}
        joint_rus_total_score = 0.0
        joint_rus_details = []
        if joint_grades:
            joint_semantic_13 = align_joint_semantics(joint_grades)
            joint_rus_total_score, joint_rus_details = calc_rus_score(joint_semantic_13, gender_lower)
            if joint_rus_total_score is not None and (math.isnan(joint_rus_total_score) or math.isinf(joint_rus_total_score)):
                joint_rus_total_score = 0.0

        plot_image_base64 = None
        if joint_recognizer and detected_joints:
            try:
                img_resized = cv2.resize(img_bgr, (joint_recognizer.imgsz, joint_recognizer.imgsz))
                plot_image_base64 = joint_recognizer._render_with_plt(
                    img_resized,
                    detected_joints,
                    dpv3_results.get('hand_side', 'unknown'),
                    grades=joint_grades
                )
            except Exception as plot_exc:
                print(f"DP V3 plot rendering failed: {plot_exc}")

        return {
            "success": True,
            "filename": file.filename,
            "gender": gender_lower,
            "joint_detect_13": {
                "hand_side": dpv3_results.get('hand_side', 'unknown'),
                "detected_count": len(detected_joints),
                "joints": detected_joints,
                "plot_image_base64": plot_image_base64,
                "dpv3_enhanced": True,
                "dpv3_info": {
                    "yolo_count": dpv3_results.get('yolo_count'),
                    "bfs_count": dpv3_results.get('bfs_count'),
                    "total_regions": dpv3_results.get('total_regions'),
                    "best_gray_range": dpv3_results.get('best_gray_range'),
                    "merged_blocks": dpv3_results.get('merged_blocks'),
                    "initial_gray_range": dpv3_results.get('initial_gray_range')
                }
            },
            "joint_grades": joint_grades,
            "joint_semantic_13": joint_semantic_13,
            "joint_rus_total_score": joint_rus_total_score,
            "joint_rus_details": joint_rus_details,
            "detection_algorithm": "dpv3"
        }

    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"DP V3小关节检测失败: {exc}")


@app.post("/formula-calculation")
async def formula_calculation(
    file: UploadFile = File(...),
    gender: str = Form(..., description="Gender: 'male' or 'female'"),
    real_age: str = Form(..., description="Real age in years"),
    joints: str = Form(..., description="JSON string of joint boxes"),
):
    """公式法骨龄计算：使用用户手动绘制的关节框进行分级和公式计算"""
    if not joint_grader:
        raise HTTPException(status_code=503, detail="小关节分级模型未加载")

    gender_lower = gender.lower()
    if gender_lower not in ["male", "female"]:
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

    try:
        # 解析关节框数据
        try:
            joint_boxes = json.loads(joints)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid joints JSON format")

        content = await file.read()
        validate_image_content(content)

        # 将用户绘制的关节框转换为模型需要的格式
        detected_joints = {}
        for joint_box in joint_boxes:
            joint_id = joint_box.get("id")
            if joint_id in RUS_13:
                detected_joints[joint_id] = {
                    "bbox_xyxy": [
                        joint_box.get("x", 0),
                        joint_box.get("y", 0),
                        joint_box.get("x", 0) + joint_box.get("width", 0),
                        joint_box.get("y", 0) + joint_box.get("height", 0)
                    ],
                    "score": 1.0
                }

        # 调用关节分级模型
        joint_grades = {}
        try:
            joint_grades = joint_grader.predict_detected_joints(
                content,
                detected_joints,
                JOINT_IMG_SIZE,
                IMAGENET_MEAN,
                IMAGENET_STD,
            )
        except Exception as joint_exc:
            print(f"Joint grading failed: {joint_exc}")
            raise HTTPException(status_code=500, detail=f"关节分级失败: {joint_exc}")

        # 语义对齐和RUS评分计算
        joint_semantic_13 = align_joint_semantics(joint_grades)
        total_score, rus_details = calc_rus_score(joint_semantic_13, gender_lower)
        if total_score is not None and (math.isnan(total_score) or math.isinf(total_score)):
            total_score = 0.0

        # 使用RUS-CHN公式计算骨龄
        bone_age = calc_bone_age_from_score(total_score, gender_lower)

        # 计算置信度（基于关节数量和质量）
        joint_count = len([j for j in joint_grades.values() if j.get("grade_raw") is not None])
        confidence = (joint_count / len(RUS_13)) * 100

        # 构建返回结果
        return {
            "success": True,
            "filename": file.filename,
            "gender": gender_lower,
            "real_age": real_age,
            "formula_name": "RUS-CHN 骨龄评估公式",
            "formula_description": "基于13个关键小关节的成熟度评分计算骨龄，使用RUS-CHN标准",
            "formula_expression": get_formula_expression(gender_lower),
            "total_score": total_score,
            "bone_age": round(bone_age, 2) if (bone_age is not None and not math.isnan(bone_age) and not math.isinf(bone_age)) else 0.0,
            "confidence": round(confidence, 1) if (confidence is not None and not math.isnan(confidence) and not math.isinf(confidence)) else 0.0,
            "joint_grades": joint_grades,
            "joint_semantic_13": joint_semantic_13,
            "joint_rus_details": rus_details,
            "joint_count": joint_count,
            "total_joints": len(RUS_13)
        }
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"公式法计算失败: {exc}")


class ManualGradeRequest(BaseModel):
    gender: str = Field(..., description="Gender: 'male' or 'female'")
    grades: Dict[str, int] = Field(..., description="Joint grades, e.g., {'Radius': 5, 'Ulna': 4, ...}")


@app.post("/manual-grade-calculation")
async def manual_grade_calculation(request: ManualGradeRequest):
    """
    手动输入关节分级计算骨龄接口：
    用户手动输入13个小关节的分级（0-14级），系统计算RUS总分和骨龄。
    """
    gender_lower = request.gender.lower()
    if gender_lower not in ["male", "female"]:
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

    grades = request.grades
    
    joint_semantic_13 = {}
    for joint_name in RUS_13:
        grade_raw = grades.get(joint_name)
        if grade_raw is not None:
            joint_semantic_13[joint_name] = {
                "grade_raw": int(grade_raw),
                "score": 1.0,
                "status": "ok",
                "imputed": False,
                "source_joint": joint_name,
            }
        else:
            joint_semantic_13[joint_name] = {
                "grade_raw": 0,
                "score": 0.0,
                "status": "missing",
                "imputed": True,
                "source_joint": joint_name,
            }

    total_score, rus_details = calc_rus_score(joint_semantic_13, gender_lower)
    bone_age = calc_bone_age_from_score(total_score, gender_lower)

    joint_count = len([g for g in grades.values() if g is not None])
    confidence = (joint_count / len(RUS_13)) * 100

    return {
        "success": True,
        "gender": gender_lower,
        "formula_name": "RUS-CHN 骨龄评估公式",
        "formula_description": "基于13个关键小关节的成熟度评分计算骨龄，使用RUS-CHN标准",
        "formula_expression": get_formula_expression(gender_lower),
        "total_score": total_score,
        "bone_age": round(bone_age, 2) if (bone_age is not None and not math.isnan(bone_age) and not math.isinf(bone_age)) else 0.0,
        "confidence": round(confidence, 1) if (confidence is not None and not math.isnan(confidence) and not math.isinf(confidence)) else 0.0,
        "joint_grades": {k: {"grade_raw": v} for k, v in grades.items() if v is not None},
        "joint_semantic_13": joint_semantic_13,
        "joint_rus_details": rus_details,
        "joint_count": joint_count,
        "total_joints": len(RUS_13)
    }


def get_formula_expression(gender: str) -> str:
    """获取RUS-CHN公式表达式"""
    if gender == "male":
        return "骨龄 = 2.018 + (-0.093)×S + 0.0033×S² + (-3.33×10⁻⁵)×S³ + 1.76×10⁻⁷×S⁴ + (-5.60×10⁻¹⁰)×S⁵ + 1.13×10⁻¹²×S⁶ + (-1.45×10⁻¹⁵)×S⁷ + 1.15×10⁻¹⁸×S⁸ + (-5.16×10⁻²²)×S⁹ + 9.94×10⁻²⁶×S¹⁰"
    else:
        return "骨龄 = 5.812 + (-0.272)×S + 0.0053×S² + (-4.38×10⁻⁵)×S³ + 2.09×10⁻⁷×S⁴ + (-6.22×10⁻¹⁰)×S⁵ + 1.20×10⁻¹²×S⁶ + (-1.49×10⁻¹⁵)×S⁷ + 1.16×10⁻¹⁸×S⁸ + (-5.13×10⁻²²)×S⁹ + 9.79×10⁻²⁶×S¹⁰"
