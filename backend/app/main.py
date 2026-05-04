import asyncio
import os
import glob
import math
import base64
import hashlib
import hmac
import ipaddress
import json
import secrets
import sqlite3
import re
import time
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms.functional as TF
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    Request,
    Response,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import ai_consult
from app.detector_of_bone.main import FractureDetector
from app.joint_assessment import (
    FINGER_LABELS_EN,
    RUS_13,
    SmallJointRecognizer,
    _resolve_hand_side,
    _resolve_hand_side_from_regions,
    align_joint_semantics,
    rename_dpv3_regions_to_named_joints,
    run_joint_assessment_pipeline,
    semantic_align_missing_joint_grades,
    standardize_detected_joints_to_rus,
)
from app.utils.gradcam import GradCAM, overlay_heatmap
from app.utils.foreign_object_detection import (
    ANOMALY_SCORE_THRESHOLD,
    build_foreign_object_detection,
)
from app.utils.growth_standards import predict_adult_height
from app.utils.notification_service import NotificationService
from app.utils.rus_chn import (
    calc_bone_age_from_score,
    calc_rus_score as calc_rus_score_util,
    generate_bone_report,
)
from dp_bone_detector_v3 import DPV3BoneDetector

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(APP_DIR)


def resolve_backend_path(path: str) -> str:
    if not path:
        return path
    if os.path.isabs(path):
        return path

    candidates = [
        os.path.abspath(path),
        os.path.abspath(os.path.join(BACKEND_DIR, path)),
        os.path.abspath(os.path.join(APP_DIR, path)),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    return candidates[1]


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


class Stage1JointModel(nn.Module):
    """
    Keep aligned with `训练代码/1/training.py` stage1_source_feature_learning:
    - backbone: resnet50
    - head: Dropout(0.2) + Linear(2048, num_classes)
    """

    def __init__(self, num_classes: int):
        super().__init__()
        base = models.resnet50(weights=None)
        feat_dim = base.fc.in_features
        base.fc = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(feat_dim, num_classes),
        )
        self.backbone = base

    def forward(self, x):
        return self.backbone(x)

    def load_state_dict(self, state_dict, strict: bool = True):
        return self.backbone.load_state_dict(state_dict, strict=strict)


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

    def _candidate_checkpoint_paths(self, joint: str) -> List[str]:
        preferred_stage1 = os.path.join(self.model_dir, f"stage1_{joint}_model.pth")
        preferred_stage1_nested = os.path.join(
            self.model_dir, joint, f"stage1_{joint}_model.pth"
        )
        direct = os.path.join(self.model_dir, f"best_{joint}.pth")
        nested = os.path.join(self.model_dir, joint, f"best_{joint}.pth")

        candidates: List[str] = []
        for path in (preferred_stage1, preferred_stage1_nested, direct, nested):
            if os.path.exists(path):
                candidates.append(path)

        recursive_patterns = [
            os.path.join(self.model_dir, "**", f"stage1_{joint}_model.pth"),
            os.path.join(self.model_dir, "**", f"best_{joint}.pth"),
        ]
        for pattern in recursive_patterns:
            for path in sorted(glob.glob(pattern, recursive=True)):
                if path not in candidates and os.path.exists(path):
                    candidates.append(path)

        return candidates

    @staticmethod
    def _normalize_class_to_idx(class_to_idx: Dict[Any, Any]) -> Dict[int, int]:
        normalized: Dict[int, int] = {}
        for raw_cls, idx in class_to_idx.items():
            normalized[int(raw_cls)] = int(idx)
        return normalized

    @staticmethod
    def _infer_num_classes_from_state_dict(
        state_dict: Dict[str, Any],
    ) -> Optional[int]:
        for key in (
            "fc.1.weight",
            "fc.weight",
            "fc.0.weight",
            "classifier.1.weight",
            "classifier.weight",
        ):
            weight = state_dict.get(key)
            if torch.is_tensor(weight) and weight.ndim >= 1:
                return int(weight.shape[0])
        return None

    @staticmethod
    def _build_stage1_idx_to_class(num_classes: int) -> Dict[int, int]:
        # Stage1 training uses numeric grade folders like 1..N and subtracts
        # 1 only for CrossEntropy labels, so inference must map back with +1.
        return {idx: idx + 1 for idx in range(num_classes)}

    @staticmethod
    def _forward_logits(item: Dict[str, Any], x: torch.Tensor) -> torch.Tensor:
        model_kind = item.get("kind", "dann")
        model = item["model"]
        if model_kind == "dann":
            logits, _, _ = model(x, lambda_grl=0.0)
            return logits
        return model(x)

    def load_all(self, joint_names: List[str]):
        loaded = 0
        for joint in joint_names:
            checkpoint_candidates = self._candidate_checkpoint_paths(joint)
            if not checkpoint_candidates:
                print(
                    f"WARNING: joint model not found for {joint} under {self.model_dir}"
                )
                continue

            loaded_this_joint = False
            for p in checkpoint_candidates:
                try:
                    ckpt = torch.load(p, map_location=self.device)
                    sd = self._extract_state_dict(ckpt)
                    class_to_idx = (
                        ckpt.get("class_to_idx", None)
                        if isinstance(ckpt, dict)
                        else None
                    )
                    model_kind = "dann"

                    if class_to_idx:
                        normalized_class_to_idx = self._normalize_class_to_idx(
                            class_to_idx
                        )
                        num_classes = len(normalized_class_to_idx)
                        idx_to_class = {
                            v: k for k, v in normalized_class_to_idx.items()
                        }

                        # Strictly match training architecture and enforce strict load.
                        m = DANNHyperModel(num_classes=num_classes)
                        m.load_state_dict(sd, strict=True)
                    else:
                        num_classes = self._infer_num_classes_from_state_dict(sd)
                        if num_classes is None:
                            print(
                                f"WARNING: class_to_idx/head metadata missing in {p}, skip"
                            )
                            continue

                        idx_to_class = self._build_stage1_idx_to_class(num_classes)
                        m = Stage1JointModel(num_classes=num_classes)
                        m.load_state_dict(sd, strict=True)
                        model_kind = "stage1"

                    m.to(self.device)
                    m.eval()

                    self.models[joint] = {
                        "model": m,
                        "kind": model_kind,
                        "idx_to_class": idx_to_class,
                        "path": p,
                    }
                    loaded += 1
                    loaded_this_joint = True
                    print(
                        f"Loaded joint model: {joint} ({num_classes} classes, {model_kind}) <- {p}"
                    )
                    break
                except Exception as exc:
                    print(f"WARNING: failed to load joint model {p}: {exc}")

            if not loaded_this_joint:
                print(f"WARNING: no usable checkpoint found for {joint}")

        print(f"Joint models loaded: {loaded}")

    def preprocess(
        self, image_bytes: bytes, img_size: int, mean: np.ndarray, std: np.ndarray
    ):
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

    def preprocess_patch(
        self, patch_bgr: np.ndarray, img_size: int, mean: np.ndarray, std: np.ndarray
    ):
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
    def _safe_crop(
        img_bgr: np.ndarray, bbox_xyxy: List[float], expand_ratio: float = 0.08
    ):
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

    # 这里是小关节分级逻辑，去掉了对图像的预处理

    @torch.no_grad()
    def predict(
        self, image_bytes: bytes, img_size: int, mean: np.ndarray, std: np.ndarray
    ):
        if not self.models:
            return {}

        x = self.preprocess(image_bytes, img_size, mean, std)
        out = {}

        for joint, item in self.models.items():
            logits = self._forward_logits(item, x)
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
        crop_canvas_size: int,
        patch_size: int,
        mean: np.ndarray,
        std: np.ndarray,
    ):
        if not self.models or not detected_joints:
            return {}

        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr_orig = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr_orig is None:
            raise ValueError("Could not decode image for detected-joint grading")
        img_bgr_resized = cv2.resize(
            img_bgr_orig, (crop_canvas_size, crop_canvas_size)
        )

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

            bbox_space = det.get("bbox_space")
            crop_source = img_bgr_orig if bbox_space == "original" else img_bgr_resized
            patch = self._safe_crop(crop_source, bbox)
            if patch is None:
                out[joint_name] = {
                    "model_joint": model_joint,
                    "grade_idx": None,
                    "grade_raw": None,
                    "score": 0.0,
                    "status": "crop_invalid",
                }
                continue

            # The stage1 joint classifier was trained on 256x256 crops. Keep the
            # detection canvas size separate from the classifier input size.
            x = self.preprocess_patch(patch, patch_size, mean, std)
            logits = self._forward_logits(self.models[model_joint], x)
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
# RUS scoring helper
# ----------------------------
def calc_rus_score(aligned_13: Dict, gender: str):
    return calc_rus_score_util(aligned_13, gender)


# ----------------------------
# Config
# ----------------------------
FOLD_MODEL_PATHS = [
    resolve_backend_path("app/models/model_fold_0.pth"),
    resolve_backend_path("app/models/model_fold_1.pth"),
    resolve_backend_path("app/models/model_fold_2.pth"),
    resolve_backend_path("app/models/model_fold_3.pth"),
    resolve_backend_path("app/models/model_fold_4.pth"),
]
EXTRA_FOLD_CANDIDATES = [
    resolve_backend_path("app/models/model_fold_0 (1).pth"),
    resolve_backend_path("app/models/model_fold_1 (1).pth"),
    resolve_backend_path("app/models/model_fold_2 (1).pth"),
    resolve_backend_path("app/models/model_fold_3 (1).pth"),
    resolve_backend_path("app/models/model_fold_4 (1).pth"),
]

JOINT_MODEL_DIR = resolve_backend_path(
    os.getenv("JOINT_MODEL_DIR", "app/models/joints")
)
JOINT_NAMES = [
    "DIP",
    "DIPFirst",
    "PIP",
    "PIPFirst",
    "MCP",
    "MCPFirst",
    "MIP",
    "Radius",
    "Ulna",
]

DEFAULT_AGE_MIN = 1.0
DEFAULT_AGE_MAX = 228.0

IMG_SIZE = 256
JOINT_MODEL_INPUT_SIZE = IMG_SIZE
JOINT_DETECTION_CANVAS_SIZE = 1024
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

FRACTURE_MODEL_PATH = resolve_backend_path(
    os.getenv(
        "FRACTURE_MODEL_PATH",
        "app/detector_of_bone/weight/yolov7-p6-bonefracture.onnx",
    )
)
JOINT_RECOGNIZE_MODEL_PATH = resolve_backend_path(
    os.getenv("JOINT_RECOGNIZE_MODEL_PATH", "app/models/recognize/best.pt")
)
AUTH_DB_PATH = os.getenv("AUTH_DB_PATH", "app/data/auth.db")
PREDICTION_DB_PATH = os.getenv("PREDICTION_DB_PATH", "app/data/predictions.db")
AUTH_TOKEN_EXPIRE_HOURS = int(os.getenv("AUTH_TOKEN_EXPIRE_HOURS", "24"))
PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "210000"))
LEGACY_ADMIN_REGISTER_KEY = os.getenv("ADMIN_REGISTER_KEY", "")
LEGACY_ADMIN_SELF_REGISTER_ENABLED = (
    os.getenv("ADMIN_SELF_REGISTER_ENABLED", "false").lower() == "true"
)
DOCTOR_REGISTER_KEY = os.getenv("DOCTOR_REGISTER_KEY", LEGACY_ADMIN_REGISTER_KEY)
DOCTOR_SELF_REGISTER_ENABLED = (
    os.getenv(
        "DOCTOR_SELF_REGISTER_ENABLED",
        "true" if LEGACY_ADMIN_SELF_REGISTER_ENABLED else "false",
    ).lower()
    == "true"
)
SUPER_ADMIN_INIT_PASSWORD = os.getenv("SUPER_ADMIN_INIT_PASSWORD", "").strip()
DEFAULT_SUPER_ADMIN_USERNAME = "admin"
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "boneage_session")
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
AUTH_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()
ALLOWED_ORIGINS = [
    item.strip()
    for item in os.getenv(
        "ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
    ).split(",")
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
DEEPSEEK_TIMEOUT_SECONDS = float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "60"))
SESSION_CLEANUP_INTERVAL_SECONDS = int(
    os.getenv("SESSION_CLEANUP_INTERVAL_SECONDS", "3600")
)

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
_gradcam_lock = Lock()


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
    global \
        models_ensemble, \
        fracture_detector, \
        joint_grader, \
        joint_recognizer, \
        dpv3_detector

    init_auth_db()
    init_prediction_db()
    session_cleanup_task = asyncio.create_task(_cleanup_expired_sessions_loop())

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
            models_ensemble.append(
                {"model": m, "age_min": age_min, "age_max": age_max, "path": p}
            )
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

    try:
        yield
    finally:
        session_cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await session_cleanup_task

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
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS or ["127.0.0.1", "localhost"]
)


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
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' http: https:; frame-ancestors 'none';"
    )
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
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_user_id ON {table_name}(user_id)"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_expires_at ON {table_name}(expires_at)"
    )


def _create_auth_rate_limits_table(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_rate_limits (
            scope TEXT NOT NULL,
            client_key TEXT NOT NULL,
            attempted_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_lookup
        ON auth_rate_limits(scope, client_key, attempted_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_attempted_at
        ON auth_rate_limits(attempted_at)
        """
    )


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

    legacy_users = conn.execute(
        "SELECT COUNT(1) FROM users WHERE role = 'admin'"
    ).fetchone()
    if legacy_users and int(legacy_users[0]) > 0:
        return True

    legacy_sessions = conn.execute(
        "SELECT COUNT(1) FROM sessions WHERE role = 'admin'"
    ).fetchone()
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
    conn.execute(
        "INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table_name, max_id)
    )


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
                else (
                    _normalize_role_value(row["role"])
                    if _is_valid_role(row["role"])
                    else ROLE_USER
                ),
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
    print(
        "Auth role schema migrated to user/doctor/super_admin and sessions were cleared"
    )


def _require_super_admin_init_password() -> str:
    if not _validate_password_strength(SUPER_ADMIN_INIT_PASSWORD):
        raise RuntimeError(
            "SUPER_ADMIN_INIT_PASSWORD must include upper/lower letters and digits, minimum 8 chars"
        )
    return SUPER_ADMIN_INIT_PASSWORD


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

    bootstrap_password = _require_super_admin_init_password()
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
    print(f"Created bootstrap super admin '{DEFAULT_SUPER_ADMIN_USERNAME}'")
def init_auth_db():
    with get_auth_conn() as conn:
        _create_users_table(conn)
        _create_sessions_table(conn)
        _create_auth_rate_limits_table(conn)
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_qa_owner_user_id ON qa_questions(owner_user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_qa_created_at ON qa_questions(created_at)"
        )
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
        _ensure_default_super_admin(conn)
        cleanup_expired_sessions(conn)
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_predictions_user_id ON predictions(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp)"
        )
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_bone_age_points_user_id ON bone_age_points(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_bone_age_points_point_time ON bone_age_points(point_time)"
        )
        conn.commit()

    # One-way migration from legacy predictions table in auth DB.
    try:
        with get_prediction_conn() as pred_conn:
            pred_count = int(
                pred_conn.execute("SELECT COUNT(1) FROM predictions").fetchone()[0]
            )
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


def verify_password(
    password: str, salt_hex: str, iterations: int, expected_hash: str
) -> bool:
    computed = hash_password(password, salt_hex, iterations)
    return hmac.compare_digest(computed, expected_hash)


def cleanup_expired_sessions(conn: sqlite3.Connection):
    now_iso = _to_iso(_utc_now())
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_iso,))


async def _cleanup_expired_sessions_loop():
    try:
        while True:
            await asyncio.sleep(SESSION_CLEANUP_INTERVAL_SECONDS)
            with get_auth_conn() as conn:
                cleanup_expired_sessions(conn)
                conn.commit()
    except asyncio.CancelledError:
        return


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
        return None
    return row


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
    now = _utc_now()
    now_iso = _to_iso(now)
    cutoff_iso = _to_iso(now - timedelta(seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS))

    with get_auth_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "DELETE FROM auth_rate_limits WHERE attempted_at <= ?",
            (cutoff_iso,),
        )
        row = conn.execute(
            """
            SELECT COUNT(1)
            FROM auth_rate_limits
            WHERE scope = ? AND client_key = ? AND attempted_at > ?
            """,
            (scope, host, cutoff_iso),
        ).fetchone()
        attempt_count = int(row[0]) if row else 0
        if attempt_count >= AUTH_RATE_LIMIT_MAX_ATTEMPTS:
            conn.commit()
            raise HTTPException(
                status_code=429, detail="Too many requests, please retry later"
            )
        conn.execute(
            """
            INSERT INTO auth_rate_limits (scope, client_key, attempted_at)
            VALUES (?, ?, ?)
            """,
            (scope, host, now_iso),
        )
        conn.commit()


def _set_auth_cookie(response: Response, token: str, expires_at_iso: str):
    expires_dt = _from_iso(expires_at_iso)
    max_age = max(int((expires_dt - _utc_now()).total_seconds()), 0)
    samesite = (
        AUTH_COOKIE_SAMESITE
        if AUTH_COOKIE_SAMESITE in {"lax", "strict", "none"}
        else "lax"
    )
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


def _validate_email_recipient(recipient: str) -> str:
    normalized = recipient.strip()
    if not re.fullmatch(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}", normalized
    ):
        raise HTTPException(status_code=400, detail="Invalid email recipient")
    domain = normalized.rsplit("@", 1)[-1].lower()
    if domain.endswith(".internal") or domain.endswith(".local"):
        raise HTTPException(
            status_code=400, detail="Email recipient domain is not allowed"
        )
    return normalized


def _validate_webhook_url(webhook_url: str) -> str:
    normalized = webhook_url.strip()
    parsed = urlsplit(normalized)
    if parsed.scheme.lower() != "https":
        raise HTTPException(status_code=400, detail="Webhook URL must use HTTPS")
    if not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Webhook URL is invalid")

    hostname = parsed.hostname.strip().lower()
    if hostname in {"localhost"} or hostname.endswith(".local"):
        raise HTTPException(status_code=400, detail="Webhook host is not allowed")

    try:
        ip_addr = ipaddress.ip_address(hostname)
    except ValueError:
        return normalized

    if (
        ip_addr.is_private
        or ip_addr.is_loopback
        or ip_addr.is_link_local
        or ip_addr.is_reserved
        or ip_addr.is_multicast
        or ip_addr.is_unspecified
    ):
        raise HTTPException(status_code=400, detail="Webhook host is not allowed")
    return normalized


def _validate_notification_recipient(method: str, recipient: str) -> str:
    method_lower = method.lower()
    if method_lower == "email":
        return _validate_email_recipient(recipient)
    if method_lower in {"wechat", "feishu"}:
        return _validate_webhook_url(recipient)
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported method: {method}. Supported: email, wechat, feishu",
    )


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


def preprocess_image_bytes(
    image_bytes: bytes, brightness: float = 0.0, contrast: float = 1.0
) -> bytes:
    img = validate_image_content(image_bytes)

    if contrast != 1.0 or brightness != 0.0:
        img = cv2.convertScaleAbs(img, alpha=contrast, beta=brightness)

    ok, buffer = cv2.imencode(".jpg", img)
    if not ok:
        raise ValueError("Could not encode image")
    return buffer.tobytes()


def preprocess_image(
    image_bytes: bytes, brightness: float = 0.0, contrast: float = 1.0
):
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


def predict_with_ensemble_tta_months(
    img_tensor: torch.Tensor, gender_tensor: torch.Tensor
):
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
        with _gradcam_lock:
            cam_model = models_ensemble[0]["model"]
            target = cam_model.backbone.layer4[-1]

            img_cam = img_tensor.clone().detach()
            img_cam.requires_grad = True

            with GradCAM(cam_model, target) as grad_cam:
                _, cam_mask = grad_cam(img_cam, gender_tensor)

        heatmap_img = overlay_heatmap(img_cam.detach().cpu(), cam_mask)
        ok, buffer = cv2.imencode(".jpg", heatmap_img)
        if not ok:
            return None

        heatmap_b64 = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/jpeg;base64,{heatmap_b64}"
    except Exception as exc:
        print(f"GradCAM failed: {exc}")
        return None


def prepare_analysis_image_bytes(
    image_bytes: bytes,
    preprocessing_enabled: bool = False,
    brightness: float = 0.0,
    contrast: float = 1.0,
) -> bytes:
    validate_image_content(image_bytes)

    if not preprocessing_enabled:
        return image_bytes

    try:
        return preprocess_image_bytes(
            image_bytes, brightness=brightness, contrast=contrast
        )
    except Exception as exc:
        print(f"Image preprocessing failed, fallback to original bytes: {exc}")
        return image_bytes


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
        raise HTTPException(
            status_code=400, detail=f"Role must be one of '{allowed_display}'"
        )
    return role


@app.post("/auth/register")
def auth_register(payload: RegisterRequest, request: Request, response: Response):
    _check_auth_rate_limit(request, "register")
    role = _parse_role_or_raise(payload.role, {ROLE_USER, ROLE_DOCTOR})

    username = payload.username.strip()
    if not _validate_username(username):
        raise HTTPException(status_code=400, detail="Username format invalid")
    if not _validate_password_strength(payload.password):
        raise HTTPException(
            status_code=400,
            detail="Password must include upper/lower letters and digits, minimum 8 chars",
        )

    if role == ROLE_DOCTOR:
        if not DOCTOR_SELF_REGISTER_ENABLED:
            raise HTTPException(
                status_code=403, detail="Doctor self-register is disabled"
            )
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
        raise HTTPException(
            status_code=400, detail="Target user must be a personal user"
        )
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
def auth_create_user(
    payload: AccountCreateRequest, request: Request, response: Response
):
    _require_super_admin(request)
    role = _parse_role_or_raise(payload.role, VALID_ROLES)
    username = payload.username.strip()
    if not _validate_username(username):
        raise HTTPException(status_code=400, detail="Username format invalid")
    if not _validate_password_strength(payload.password):
        raise HTTPException(
            status_code=400,
            detail="Password must include upper/lower letters and digits, minimum 8 chars",
        )

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
def auth_update_user_role(
    target_user_id: int, payload: AccountRoleUpdateRequest, request: Request
):
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
        if (
            current_role == ROLE_SUPER_ADMIN
            and new_role != ROLE_SUPER_ADMIN
            and _count_super_admins(conn) <= 1
        ):
            raise HTTPException(
                status_code=400, detail="At least one super admin must remain"
            )

        conn.execute(
            "UPDATE users SET role = ? WHERE id = ?", (new_role, target_user_id)
        )
        _invalidate_user_sessions(conn, target_user_id)
        conn.commit()

    return {"success": True, "id": target_user_id, "role": new_role}


@app.delete("/auth/users/{target_user_id}")
def auth_delete_user(target_user_id: int, request: Request):
    session = _require_super_admin(request)

    if int(session["user_id"]) == target_user_id:
        raise HTTPException(
            status_code=400, detail="You cannot delete your own account"
        )

    with get_auth_conn() as conn:
        row = conn.execute(
            "SELECT id, username, role FROM users WHERE id = ?",
            (target_user_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        target_role = _normalize_role_value(row["role"])
        if target_role == ROLE_SUPER_ADMIN and _count_super_admins(conn) <= 1:
            raise HTTPException(
                status_code=400, detail="At least one super admin must remain"
            )

        _delete_prediction_records_for_user(target_user_id)
        _invalidate_user_sessions(conn, target_user_id)
        conn.execute(
            "DELETE FROM qa_questions WHERE owner_user_id = ?", (target_user_id,)
        )
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
        rows = conn.execute(
            "SELECT id, author_name, title, content, created_at FROM articles ORDER BY id DESC"
        ).fetchall()
    return {"success": True, "items": [dict(r) for r in rows]}


@app.post("/articles")
def create_article(payload: ArticleCreateRequest, request: Request):
    session = _require_doctor(request)
    now_iso = _to_iso(_utc_now())
    with get_auth_conn() as conn:
        conn.execute(
            "INSERT INTO articles (author_id, author_name, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                session["user_id"],
                session["username"],
                payload.title,
                payload.content,
                now_iso,
            ),
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


def _fetch_prediction_row_for_session(
    pred_id: str, session: sqlite3.Row
) -> sqlite3.Row:
    with get_prediction_conn() as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE id = ?", (pred_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if not _is_doctor_or_above(session["role"]) and int(row["user_id"]) != int(
        session["user_id"]
    ):
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
        elapsed_years = (float(p["point_time"]) - base_t) / (
            1000.0 * 60.0 * 60.0 * 24.0 * 365.25
        )
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
        "coefficients": {
            "intercept": round(b0, 6),
            "time": round(b1, 6),
            "chronological_age": round(b2, 6),
        },
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
            (
                int(session["user_id"]),
                session["username"],
                text,
                image,
                now_iso,
                now_iso,
            ),
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
            cur = conn.execute(
                "DELETE FROM qa_questions WHERE owner_user_id = ?", (user_id,)
            )
        conn.commit()
    return {"success": True, "deleted": int(cur.rowcount)}


@app.post("/send_notification")
async def send_notification(payload: NotificationRequest, request: Request):
    _require_doctor(request)
    method = payload.method.lower()
    recipient = _validate_notification_recipient(method, payload.recipient)
    try:
        if method == "email":
            return await NotificationService.send_email(
                recipient=recipient,
                report_data=payload.report_data,
                remarks=payload.remarks,
                custom_template=payload.custom_template,
                report_id=payload.report_id,
            )
        if method == "wechat":
            return await NotificationService.send_wechat_webhook(
                webhook_url=recipient,
                report_data=payload.report_data,
                remarks=payload.remarks,
                custom_template=payload.custom_template,
                report_id=payload.report_id,
            )
        if method == "feishu":
            return await NotificationService.send_feishu_webhook(
                webhook_url=recipient,
                report_data=payload.report_data,
                remarks=payload.remarks,
                custom_template=payload.custom_template,
                report_id=payload.report_id,
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
    real_age_years: Optional[float] = Form(
        None, description="Chronological age in years"
    ),
    target_user_id: Optional[int] = Form(
        default=None, description="Personal user id for doctor-created predictions"
    ),
    preprocessing_enabled: bool = Form(False),
    brightness: float = Form(0.0),
    contrast: float = Form(1.0),
    use_dpv3: bool = Form(True, description="是否使用DP V3增强关节检测"),
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
        processed_content = prepare_analysis_image_bytes(
            content,
            preprocessing_enabled=preprocessing_enabled,
            brightness=brightness,
            contrast=contrast,
        )

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

        joint_analysis = run_joint_assessment_pipeline(
            processed_content,
            gender_lower,
            joint_grader=joint_grader,
            joint_recognizer=joint_recognizer,
            dpv3_detector=dpv3_detector,
            joint_detection_canvas_size=JOINT_DETECTION_CANVAS_SIZE,
            joint_model_input_size=JOINT_MODEL_INPUT_SIZE,
            imagenet_mean=IMAGENET_MEAN,
            imagenet_std=IMAGENET_STD,
            use_dpv3=use_dpv3,
        )
        recognized_joints_13 = joint_analysis["joint_detect_13"]
        joint_grades = joint_analysis["joint_grades"]
        joint_semantic_13 = joint_analysis["joint_semantic_13"]
        joint_rus_total_score = joint_analysis["joint_rus_total_score"]
        joint_rus_details = joint_analysis["joint_rus_details"]
        rus_bone_age_years = joint_analysis["rus_bone_age_years"]
        detection_algorithm = joint_analysis["detection_algorithm"]

        img_tensor = preprocess_image(processed_content).to(device)

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
            "rus_bone_age_years": round(rus_bone_age_years, 2)
            if rus_bone_age_years is not None
            else None,
            "joint_rus_details": joint_rus_details,
            "joint_detect_13": recognized_joints_13,
            "detection_algorithm": detection_algorithm,
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
            rows = conn.execute(
                "SELECT id, user_id, timestamp, filename, predicted_age_years, gender FROM predictions ORDER BY timestamp DESC LIMIT 100"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, timestamp, filename, predicted_age_years, gender FROM predictions WHERE user_id = ? ORDER BY timestamp DESC",
                (user_id,),
            ).fetchall()
    items = [{k: r[k] for k in r.keys()} for r in rows]
    if _is_doctor_or_above(role):
        usernames = _fetch_usernames_by_ids(
            [int(item["user_id"]) for item in items if item.get("user_id") is not None]
        )
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
    data["foreign_object_detection"] = build_foreign_object_detection(
        data.get("anomalies")
    )
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

    if (
        update_fields["predicted_age_years"] is not None
        and update_fields["predicted_age_months"] is None
    ):
        update_fields["predicted_age_months"] = (
            float(update_fields["predicted_age_years"]) * 12.0
        )

    for key, val in update_fields.items():
        if val is not None:
            full_json[key] = val
    full_json["foreign_object_detection"] = build_foreign_object_detection(
        full_json.get("anomalies")
    )

    new_filename = (
        update_fields["filename"]
        if update_fields["filename"] is not None
        else row["filename"]
    )
    new_timestamp = (
        int(update_fields["timestamp"])
        if update_fields["timestamp"] is not None
        else int(row["timestamp"])
    )
    new_gender = (
        update_fields["gender"]
        if update_fields["gender"] is not None
        else row["gender"]
    )
    new_months = (
        float(update_fields["predicted_age_months"])
        if update_fields["predicted_age_months"] is not None
        else float(row["predicted_age_months"])
    )
    new_years = (
        float(update_fields["predicted_age_years"])
        if update_fields["predicted_age_years"] is not None
        else float(row["predicted_age_years"])
    )
    new_real_age = (
        update_fields["real_age_years"]
        if update_fields["real_age_years"] is not None
        else row["real_age_years"]
    )
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
            (
                new_filename,
                new_timestamp,
                new_months,
                new_years,
                new_gender,
                new_real_age,
                new_height,
                json.dumps(full_json),
                pred_id,
            ),
        )
        if (
            update_fields["predicted_age_years"] is not None
            or update_fields["real_age_years"] is not None
            or update_fields["timestamp"] is not None
        ):
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
def list_bone_age_points(
    request: Request, user_id: Optional[int] = Query(default=None)
):
    session = _require_session(request)
    uid = int(session["user_id"])
    role = str(session["role"])
    target_user_id = (
        user_id if (_is_doctor_or_above(role) and user_id is not None) else uid
    )

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
        raise HTTPException(
            status_code=400, detail="bone_age_years must be a valid number > 0"
        )
    if bone_age_years > 30:
        raise HTTPException(status_code=400, detail="bone_age_years must be <= 30")

    chronological_age_years = _to_optional_float(raw_chronological_age_years)
    if chronological_age_years is not None and chronological_age_years > 30:
        raise HTTPException(
            status_code=400, detail="chronological_age_years must be <= 30"
        )

    parsed_user_id = _to_optional_int(raw_user_id)
    parsed_point_time = _to_optional_int(raw_point_time)
    note = str(raw_note or "").strip()[:500]

    target_user_id = (
        parsed_user_id
        if (_is_doctor_or_above(role) and parsed_user_id is not None)
        else uid
    )
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    point_time = parsed_point_time if parsed_point_time is not None else now_ts
    now_iso = _to_iso(_utc_now())

    with get_prediction_conn() as conn:
        conn.execute(
            """
            INSERT INTO bone_age_points (user_id, point_time, bone_age_years, chronological_age_years, source, prediction_id, note, created_at)
            VALUES (?, ?, ?, ?, 'manual', NULL, ?, ?)
            """,
            (
                target_user_id,
                point_time,
                bone_age_years,
                chronological_age_years,
                note,
                now_iso,
            ),
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
        row = conn.execute(
            "SELECT user_id FROM bone_age_points WHERE id = ?", (point_id,)
        ).fetchone()
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
    target_user_id = (
        user_id if (_is_doctor_or_above(role) and user_id is not None) else uid
    )

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
async def doctor_ai_assistant(
    payload: ai_consult.DoctorAssistantRequest, request: Request
):
    _require_doctor(request)
    ai_consult.ensure_api_key(DEEPSEEK_API_KEY, "DEEPSEEK_API_KEY is not configured")

    context_chunks: List[str] = []
    if payload.context:
        context_chunks.append(f"额外上下文: {payload.context}")
    if payload.prediction_id:
        with get_prediction_conn() as conn:
            row = conn.execute(
                "SELECT full_json FROM predictions WHERE id = ?",
                (payload.prediction_id,),
            ).fetchone()
        if row:
            context_chunks.append(
                f"预测记录[{payload.prediction_id}]: {row['full_json'][:4000]}"
            )

    messages = ai_consult.build_doctor_assistant_messages(
        payload.message, context_chunks
    )
    return StreamingResponse(
        ai_consult.stream_deepseek_chat(
            api_key=DEEPSEEK_API_KEY,
            api_base=DEEPSEEK_API_BASE,
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.2,
            timeout_seconds=DEEPSEEK_TIMEOUT_SECONDS,
            error_prefix="AI assistant failed",
        ),
        media_type="text/event-stream",
    )


@app.post("/public/ai-consult")
async def public_ai_consult(payload: ai_consult.PublicConsultRequest):
    """公开 AI 小助手接口：统一通过后端代理 DeepSeek，供首页浮窗等无登录场景使用。"""
    ai_consult.ensure_api_key(
        DEEPSEEK_API_KEY, "智能问诊服务暂未开放，请联系管理员配置 API 密钥"
    )

    messages = ai_consult.build_consult_messages(
        system_prompt=ai_consult.build_consult_system_prompt(),
        message=payload.message,
        history=payload.history,
    )
    return StreamingResponse(
        ai_consult.stream_deepseek_chat(
            api_key=DEEPSEEK_API_KEY,
            api_base=DEEPSEEK_API_BASE,
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.4,
            timeout_seconds=DEEPSEEK_TIMEOUT_SECONDS,
            error_prefix="智能问诊失败",
        ),
        media_type="text/event-stream",
    )


@app.post("/user/ai-consult")
async def user_ai_consult(payload: ai_consult.UserConsultRequest, request: Request):
    """患者智能问诊接口：任意已登录用户均可调用，prompt 偏向健康科普与就医指导。"""
    _require_session(request)
    ai_consult.ensure_api_key(
        DEEPSEEK_API_KEY, "智能问诊服务暂未开放，请联系管理员配置 API 密钥"
    )

    messages = ai_consult.build_consult_messages(
        system_prompt=ai_consult.build_consult_system_prompt(),
        message=payload.message,
        history=[],
    )
    return StreamingResponse(
        ai_consult.stream_deepseek_chat(
            api_key=DEEPSEEK_API_KEY,
            api_base=DEEPSEEK_API_BASE,
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.4,
            timeout_seconds=DEEPSEEK_TIMEOUT_SECONDS,
            error_prefix="智能问诊失败",
        ),
        media_type="text/event-stream",
    )


@app.post("/public/ai-consult-image")
async def public_ai_consult_with_image(payload: ai_consult.ImageConsultRequest):
    """公开 AI 图片问诊接口：统一通过后端代理 DeepSeek，供首页浮窗等无登录场景使用。"""
    ai_consult.ensure_api_key(
        DEEPSEEK_API_KEY, "智能问诊服务暂未开放，请联系管理员配置 API 密钥"
    )

    messages = ai_consult.build_consult_messages(
        system_prompt=ai_consult.build_consult_system_prompt(include_image=True),
        message=payload.message,
        history=payload.history,
        image_base64=payload.image_base64,
    )
    return StreamingResponse(
        ai_consult.stream_deepseek_chat(
            api_key=DEEPSEEK_API_KEY,
            api_base=DEEPSEEK_API_BASE,
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.4,
            timeout_seconds=max(DEEPSEEK_TIMEOUT_SECONDS, 120.0),
            error_prefix="智能问诊失败",
        ),
        media_type="text/event-stream",
    )


@app.post("/user/ai-consult-image")
async def user_ai_consult_with_image(
    payload: ai_consult.ImageConsultRequest, request: Request
):
    """患者智能问诊接口（支持图片）：用户可上传X光片等图片进行问诊"""
    _require_session(request)
    ai_consult.ensure_api_key(
        DEEPSEEK_API_KEY, "智能问诊服务暂未开放，请联系管理员配置 API 密钥"
    )

    messages = ai_consult.build_consult_messages(
        system_prompt=ai_consult.build_consult_system_prompt(include_image=True),
        message=payload.message,
        history=[],
        image_base64=payload.image_base64,
    )
    return StreamingResponse(
        ai_consult.stream_deepseek_chat(
            api_key=DEEPSEEK_API_KEY,
            api_base=DEEPSEEK_API_BASE,
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.4,
            timeout_seconds=max(DEEPSEEK_TIMEOUT_SECONDS, 120.0),
            error_prefix="智能问诊失败",
        ),
        media_type="text/event-stream",
    )


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
        processed_content = prepare_analysis_image_bytes(
            content,
            preprocessing_enabled=preprocessing_enabled,
            brightness=brightness,
            contrast=contrast,
        )

        joint_analysis = run_joint_assessment_pipeline(
            processed_content,
            gender_lower,
            joint_grader=joint_grader,
            joint_recognizer=joint_recognizer,
            dpv3_detector=dpv3_detector,
            joint_detection_canvas_size=JOINT_DETECTION_CANVAS_SIZE,
            joint_model_input_size=JOINT_MODEL_INPUT_SIZE,
            imagenet_mean=IMAGENET_MEAN,
            imagenet_std=IMAGENET_STD,
            use_dpv3=use_dpv3,
        )
        recognized_joints_13 = joint_analysis["joint_detect_13"]
        joint_grades = joint_analysis["joint_grades"]
        joint_semantic_13 = joint_analysis["joint_semantic_13"]
        joint_rus_total_score = joint_analysis["joint_rus_total_score"] or 0.0
        joint_rus_details = joint_analysis["joint_rus_details"]
        detection_algorithm = joint_analysis["detection_algorithm"]

        return {
            "success": True,
            "filename": file.filename,
            "gender": gender_lower,
            "joint_detect_13": recognized_joints_13,
            "joint_grades": joint_grades,
            "joint_semantic_13": joint_semantic_13,
            "joint_rus_total_score": joint_rus_total_score,
            "joint_rus_details": joint_rus_details,
            "detection_algorithm": detection_algorithm,
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
                processed_content = preprocess_image_bytes(
                    content, brightness=brightness, contrast=contrast
                )
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
        ordered_joints = []
        resolved_hand_side = dpv3_results.get("hand_side", "unknown")
        if dpv3_results.get("success"):
            detected_joints, ordered_joints, resolved_hand_side = (
                rename_dpv3_regions_to_named_joints(
                    dpv3_results.get("regions", []),
                    img_bgr.shape[:2],
                    resolved_hand_side,
                )
            )

        joint_grades = {}
        try:
            joint_grades = joint_grader.predict_detected_joints(
                processed_content,
                detected_joints,
                JOINT_DETECTION_CANVAS_SIZE,
                JOINT_MODEL_INPUT_SIZE,
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
            joint_rus_total_score, joint_rus_details = calc_rus_score(
                joint_semantic_13, gender_lower
            )
            if joint_rus_total_score is not None and (
                math.isnan(joint_rus_total_score) or math.isinf(joint_rus_total_score)
            ):
                joint_rus_total_score = 0.0

        plot_image_base64 = None
        if joint_recognizer and detected_joints:
            try:
                plot_image_base64 = joint_recognizer._render_with_plt(
                    img_bgr,
                    detected_joints,
                    resolved_hand_side,
                    grades=joint_grades,
                )
            except Exception as plot_exc:
                print(f"DP V3 plot rendering failed: {plot_exc}")

        return {
            "success": True,
            "filename": file.filename,
            "gender": gender_lower,
            "joint_detect_13": {
                "hand_side": resolved_hand_side,
                "detected_count": len(detected_joints),
                "joints": detected_joints,
                "ordered_joints": ordered_joints,
                "rus_13_joints": standardize_detected_joints_to_rus(detected_joints),
                "plot_image_base64": plot_image_base64,
                "dpv3_enhanced": True,
                "dpv3_info": {
                    "yolo_count": dpv3_results.get("yolo_count"),
                    "bfs_count": dpv3_results.get("bfs_count"),
                    "total_regions": dpv3_results.get("total_regions"),
                    "best_gray_range": dpv3_results.get("best_gray_range"),
                    "merged_blocks": dpv3_results.get("merged_blocks"),
                    "initial_gray_range": dpv3_results.get("initial_gray_range"),
                },
            },
            "joint_grades": joint_grades,
            "joint_semantic_13": joint_semantic_13,
            "joint_rus_total_score": joint_rus_total_score,
            "joint_rus_details": joint_rus_details,
            "detection_algorithm": "dpv3",
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
                        joint_box.get("y", 0) + joint_box.get("height", 0),
                    ],
                    "bbox_space": joint_box.get("bboxSpace")
                    or joint_box.get("bbox_space")
                    or "original",
                    "score": 1.0,
                }

        # 调用关节分级模型
        joint_grades = {}
        try:
            joint_grades = joint_grader.predict_detected_joints(
                content,
                detected_joints,
                JOINT_DETECTION_CANVAS_SIZE,
                JOINT_MODEL_INPUT_SIZE,
                IMAGENET_MEAN,
                IMAGENET_STD,
            )
        except Exception as joint_exc:
            print(f"Joint grading failed: {joint_exc}")
            raise HTTPException(status_code=500, detail=f"关节分级失败: {joint_exc}")

        # 语义对齐和RUS评分计算
        observed_joint_count = len(
            [j for j in joint_grades.values() if j.get("grade_raw") is not None]
        )
        joint_grades = semantic_align_missing_joint_grades(joint_grades)
        joint_semantic_13 = align_joint_semantics(joint_grades)
        total_score, rus_details = calc_rus_score(joint_semantic_13, gender_lower)
        if total_score is not None and (
            math.isnan(total_score) or math.isinf(total_score)
        ):
            total_score = 0.0

        # 使用RUS-CHN公式计算骨龄
        bone_age = calc_bone_age_from_score(total_score, gender_lower)

        # 计算置信度（基于关节数量和质量）
        joint_count = observed_joint_count
        confidence = (observed_joint_count / len(RUS_13)) * 100
        imputed_joint_count = len(
            [j for j in joint_grades.values() if bool(j.get("imputed"))]
        )

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
            "bone_age": round(bone_age, 2)
            if (
                bone_age is not None
                and not math.isnan(bone_age)
                and not math.isinf(bone_age)
            )
            else 0.0,
            "confidence": round(confidence, 1)
            if (
                confidence is not None
                and not math.isnan(confidence)
                and not math.isinf(confidence)
            )
            else 0.0,
            "joint_grades": joint_grades,
            "joint_semantic_13": joint_semantic_13,
            "joint_rus_details": rus_details,
            "joint_count": joint_count,
            "imputed_joint_count": imputed_joint_count,
            "total_joints": len(RUS_13),
        }
    except HTTPException:
        raise
    except Exception as exc:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"公式法计算失败: {exc}")


class ManualGradeRequest(BaseModel):
    gender: str = Field(..., description="Gender: 'male' or 'female'")
    grades: Dict[str, int] = Field(
        ..., description="Joint grades, e.g., {'Radius': 5, 'Ulna': 4, ...}"
    )


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
        "bone_age": round(bone_age, 2)
        if (
            bone_age is not None
            and not math.isnan(bone_age)
            and not math.isinf(bone_age)
        )
        else 0.0,
        "confidence": round(confidence, 1)
        if (
            confidence is not None
            and not math.isnan(confidence)
            and not math.isinf(confidence)
        )
        else 0.0,
        "joint_grades": {
            k: {"grade_raw": v} for k, v in grades.items() if v is not None
        },
        "joint_semantic_13": joint_semantic_13,
        "joint_rus_details": rus_details,
        "joint_count": joint_count,
        "total_joints": len(RUS_13),
    }


def get_formula_expression(gender: str) -> str:
    """获取RUS-CHN公式表达式"""
    if gender == "male":
        return "骨龄 = 2.018 + (-0.093)×S + 0.0033×S² + (-3.33×10⁻⁵)×S³ + 1.76×10⁻⁷×S⁴ + (-5.60×10⁻¹⁰)×S⁵ + 1.13×10⁻¹²×S⁶ + (-1.45×10⁻¹⁵)×S⁷ + 1.15×10⁻¹⁸×S⁸ + (-5.16×10⁻²²)×S⁹ + 9.94×10⁻²⁶×S¹⁰"
    else:
        return "骨龄 = 5.812 + (-0.272)×S + 0.0053×S² + (-4.38×10⁻⁵)×S³ + 2.09×10⁻⁷×S⁴ + (-6.22×10⁻¹⁰)×S⁵ + 1.20×10⁻¹²×S⁶ + (-1.49×10⁻¹⁵)×S⁷ + 1.16×10⁻¹⁸×S⁸ + (-5.13×10⁻²²)×S⁹ + 9.79×10⁻²⁶×S¹⁰"
