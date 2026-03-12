import os
import base64
import hashlib
import hmac
import requests
import secrets
import sqlite3
import re
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
from pydantic import BaseModel, Field
from ultralytics import YOLO

from app.utils.gradcam import GradCAM, overlay_heatmap
from app.utils.growth_standards import predict_adult_height
from app.utils.notification_service import NotificationService
from app.utils.rus_chn import generate_bone_report


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
            "MCPThird": "MCP",
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

    @torch.no_grad()
    def predict(self, image_bytes: bytes, img_size: int, mean: np.ndarray, std: np.ndarray):
        if not self.models:
            return {}

        x = self.preprocess(image_bytes, img_size, mean, std)
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

    def _render_with_plt(self, img_bgr: np.ndarray, joints: Dict[str, Dict], hand_side: str) -> Optional[str]:
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
            ax.text(
                x1,
                max(0.0, y1 - 6.0),
                f"{name} {payload['score']:.2f}",
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
        result = self.model.predict(
            source=img_bgr,
            imgsz=self.imgsz,
            conf=self.conf,
            verbose=False,
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
JOINT_IMG_SIZE = 224
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
ADMIN_REGISTER_KEY = os.getenv("ADMIN_REGISTER_KEY", "")
ADMIN_SELF_REGISTER_ENABLED = os.getenv("ADMIN_SELF_REGISTER_ENABLED", "false").lower() == "true"
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

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
models_ensemble: List[Dict] = []
fracture_detector: Optional[FractureDetector] = None
joint_grader: Optional[JointGrader] = None
joint_recognizer: Optional[SmallJointRecognizer] = None


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
    global models_ensemble, fracture_detector, joint_grader, joint_recognizer

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

    yield

    models_ensemble = []
    fracture_detector = None
    joint_grader = None
    joint_recognizer = None


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


def init_auth_db():
    with get_auth_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL CHECK (role IN ('user','admin')),
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                iterations INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user','admin')),
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)")
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
def preprocess_image(image_bytes: bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_LINEAR)
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


@app.post("/auth/register")
def auth_register(payload: RegisterRequest, request: Request, response: Response):
    _check_auth_rate_limit(request, "register")
    role = payload.role.lower().strip()
    if role not in {"user", "admin"}:
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")

    username = payload.username.strip()
    if not _validate_username(username):
        raise HTTPException(status_code=400, detail="Username format invalid")
    if not _validate_password_strength(payload.password):
        raise HTTPException(status_code=400, detail="Password must include upper/lower letters and digits, minimum 8 chars")

    if role == "admin":
        if not ADMIN_SELF_REGISTER_ENABLED:
            raise HTTPException(status_code=403, detail="Admin self-register is disabled")
        if ADMIN_REGISTER_KEY and payload.admin_key != ADMIN_REGISTER_KEY:
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
    role = payload.role.lower().strip()
    if role not in {"user", "admin"}:
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")

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
        "admin_self_register_enabled": ADMIN_SELF_REGISTER_ENABLED,
    }


def _require_admin(request: Request):
    token = _resolve_token(request, None)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with get_auth_conn() as conn:
        session_row = get_session(conn, token)
        if not session_row:
            raise HTTPException(status_code=401, detail="Session expired or invalid")
        if session_row["role"] != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")


def _require_session(request: Request) -> sqlite3.Row:
    token = _resolve_token(request, None)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with get_auth_conn() as conn:
        session_row = get_session(conn, token)
        if not session_row:
            raise HTTPException(status_code=401, detail="Session expired or invalid")
        return session_row


@app.get("/auth/admin_ping")
def auth_admin_ping(request: Request):
    _require_admin(request)
    return {"success": True}


@app.post("/auth/user_ping")
def auth_user_ping(request: Request):
    token = _resolve_token(request, None)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with get_auth_conn() as conn:
        session_row = get_session(conn, token)
        if not session_row:
            raise HTTPException(status_code=401, detail="Session expired or invalid")
    return {"success": True}


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
    session = _require_session(request)
    if session["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only doctors can post articles")
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
    if session["role"] != "admin" and int(row["user_id"]) != int(session["user_id"]):
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
    coeff, *_ = np.linalg.lstsq(x, y, rcond=None)
    y_hat = x @ coeff
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-9 else 1.0

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
        if role == "admin":
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

    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    with get_auth_conn() as conn:
        conn.execute(
            """
            INSERT INTO qa_questions (owner_user_id, owner_username, question_text, image_base64, reply_text, created_at, updated_at)
            VALUES (?, ?, ?, ?, '', ?, ?)
            """,
            (int(session["user_id"]), session["username"], text, image, now, now),
        )
        qid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()

    return {"success": True, "qid": qid}


@app.post("/qa/questions/{qid}/reply")
def qa_reply_question(qid: int, payload: QaReplyRequest, request: Request):
    _require_admin(request)
    reply = payload.reply.strip()
    if not reply:
        raise HTTPException(status_code=400, detail="Reply cannot be empty")

    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    with get_auth_conn() as conn:
        cur = conn.execute(
            "UPDATE qa_questions SET reply_text = ?, updated_at = ? WHERE id = ?",
            (reply, now, qid),
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
        if role == "admin":
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
        if role == "admin":
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
    height: float = Form(None, description="Current height in cm"),
    real_age_years: float = Form(None, description="Chronological age in years"),
):
    if not models_ensemble:
        raise HTTPException(status_code=503, detail="Age model not loaded")

    gender_lower = gender.lower()
    if gender_lower not in ["male", "female"]:
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

    gender_val = 1.0 if gender_lower == "male" else 0.0
    gender_tensor = torch.tensor([[gender_val]], dtype=torch.float32, device=device)

    try:
        content = await file.read()

        anomalies = []
        detection_image_base64 = None
        if fracture_detector:
            try:
                anomalies, detection_image_base64 = fracture_detector.detect(content)
            except Exception as det_exc:
                print(f"Fracture detect failed: {det_exc}")

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

        # Save to database if session exists
        import json
        token = _resolve_token(request, None)
        if token:
            with get_auth_conn() as conn:
                session_row = get_session(conn, token)
            if session_row:
                import time
                import uuid

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
                            session_row["user_id"],
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
                            session_row["user_id"],
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
        if role == "admin":
            rows = conn.execute("SELECT id, user_id, timestamp, filename, predicted_age_years, gender FROM predictions ORDER BY timestamp DESC LIMIT 100").fetchall()
        else:
            rows = conn.execute("SELECT id, timestamp, filename, predicted_age_years, gender FROM predictions WHERE user_id = ? ORDER BY timestamp DESC", (user_id,)).fetchall()

    return {"success": True, "items": [{k: r[k] for k in r.keys()} for r in rows]}


@app.get("/predictions/{pred_id}")
def get_prediction_detail(pred_id: str, request: Request):
    session = _require_session(request)
    row = _fetch_prediction_row_for_session(pred_id, session)

    import json

    data = json.loads(row["full_json"])
    data["id"] = pred_id
    data["timestamp"] = row["timestamp"]
    data["real_age_years"] = row["real_age_years"]
    return {"success": True, "data": data}


@app.put("/predictions/{pred_id}")
def update_prediction(pred_id: str, payload: PredictionUpdateRequest, request: Request):
    session = _require_session(request)
    row = _fetch_prediction_row_for_session(pred_id, session)

    import json

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


@app.get("/bone-age-points")
def list_bone_age_points(request: Request, user_id: Optional[int] = Query(default=None)):
    session = _require_session(request)
    uid = int(session["user_id"])
    role = str(session["role"])
    target_user_id = user_id if (role == "admin" and user_id is not None) else uid

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

    target_user_id = parsed_user_id if (role == "admin" and parsed_user_id is not None) else uid
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
        if role != "admin" and int(row["user_id"]) != uid:
            raise HTTPException(status_code=403, detail="Access denied")
        conn.execute("DELETE FROM bone_age_points WHERE id = ?", (point_id,))
        conn.commit()

    return {"success": True}


@app.get("/bone-age-trend")
def get_bone_age_trend(request: Request, user_id: Optional[int] = Query(default=None)):
    session = _require_session(request)
    uid = int(session["user_id"])
    role = str(session["role"])
    target_user_id = user_id if (role == "admin" and user_id is not None) else uid

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
def doctor_ai_assistant(payload: DoctorAssistantRequest, request: Request):
    _require_admin(request)
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
            },
            timeout=45,
        )
        if not resp.ok:
            raise HTTPException(status_code=resp.status_code, detail=f"DeepSeek API error: {resp.text[:800]}")
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise HTTPException(status_code=502, detail="DeepSeek API returned empty choices")
        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            raise HTTPException(status_code=502, detail="DeepSeek API returned empty content")
        return {"success": True, "reply": content, "model": data.get("model", DEEPSEEK_MODEL)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI assistant failed: {exc}")


class UserConsultRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@app.post("/user/ai-consult")
def user_ai_consult(payload: UserConsultRequest, request: Request):
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
            },
            timeout=45,
        )
        if not resp.ok:
            raise HTTPException(status_code=resp.status_code, detail=f"AI 服务调用失败: {resp.text[:400]}")
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise HTTPException(status_code=502, detail="AI 服务返回空结果")
        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            raise HTTPException(status_code=502, detail="AI 服务返回了空内容")
        return {"success": True, "reply": content, "model": data.get("model", DEEPSEEK_MODEL)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"智能问诊失败: {exc}")
