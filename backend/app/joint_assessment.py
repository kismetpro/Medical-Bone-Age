import base64
import math
import traceback
from typing import Any, Dict, List, Optional, Tuple

import cv2
import matplotlib
matplotlib.use("Agg")
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from ultralytics import YOLO

from app.utils.rus_chn import (
    calc_bone_age_from_score,
    calc_rus_score as calc_rus_score_util,
)


def _resolve_hand_side(
    radius_x: Optional[float], ulna_x: Optional[float], fallback: str = "unknown"
) -> str:
    if radius_x is None or ulna_x is None:
        return fallback if fallback in {"left", "right"} else "unknown"
    return "left" if float(radius_x) > float(ulna_x) else "right"


class SmallJointRecognizer:
    def __init__(self, model_path: str, imgsz: int = 1024, conf: float = 0.2):
        self.model = YOLO(model_path)
        self.imgsz = imgsz
        self.conf = conf

    def _render_with_plt(
        self,
        img_bgr: np.ndarray,
        joints: Dict[str, Dict],
        hand_side: str,
        grades: Dict[str, Dict] = None,
    ) -> Optional[str]:
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        fig = Figure(figsize=(8, 10), dpi=120)
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        ax.imshow(img_rgb)

        for name, payload in joints.items():
            x1, y1, x2, y2 = payload["bbox_xyxy"]
            rect = Rectangle(
                (x1, y1),
                x2 - x1,
                y2 - y1,
                fill=False,
                edgecolor="red",
                linewidth=2,
            )
            ax.add_patch(rect)

            label = f"{name} {payload['score']:.2f}"
            if grades and name in grades:
                grade = grades[name].get("grade_raw")
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
        canvas.draw()

        rgba = np.asarray(canvas.buffer_rgba())
        rgb = rgba[:, :, :3].copy()

        plot_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        ok, buf = cv2.imencode(".jpg", plot_bgr)
        if not ok:
            return None

        return "data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")

    def recognize_13(self, image_bytes: bytes) -> Dict:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr_orig = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr_orig is None:
            return {
                "hand_side": "unknown",
                "detected_count": 0,
                "joints": {},
                "plot_image_base64": None,
            }

        h, w = img_bgr_orig.shape[:2]
        img_bgr = cv2.resize(img_bgr_orig, (self.imgsz, self.imgsz))
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

        hand_side = _resolve_hand_side(radius_x, ulna_x)
        final_13: Dict[str, Dict] = {}

        def map_finger_logic(
            yolo_lbl: str,
            target_prefix: str,
            finger_indices: List[int],
            target_suffixes: List[str],
        ):
            subset = [d for d in all_d if d["lbl"] == yolo_lbl]
            if hand_side == "unknown":
                subset = sorted(subset, key=lambda x: x["cx"])
            else:
                subset = sorted(
                    subset,
                    key=lambda x: x["cx"],
                    reverse=(hand_side == "right"),
                )

            for idx, suffix in zip(finger_indices, target_suffixes):
                if len(subset) > idx:
                    final_13[f"{target_prefix}{suffix}"] = subset[idx]

        for d in all_d:
            if d["lbl"] == "Radius" and "Radius" not in final_13:
                final_13["Radius"] = d
            elif d["lbl"] == "Ulna" and "Ulna" not in final_13:
                final_13["Ulna"] = d

        map_finger_logic("MCP", "MCP", [0, 2, 4], ["First", "Third", "Fifth"])
        map_finger_logic(
            "ProximalPhalanx", "PIP", [0, 2, 4], ["First", "Third", "Fifth"]
        )
        map_finger_logic("MiddlePhalanx", "MIP", [1, 2], ["Third", "Fifth"])
        map_finger_logic(
            "DistalPhalanx", "DIP", [0, 2, 4], ["First", "Third", "Fifth"]
        )

        joints: Dict[str, Dict] = {}
        scale_x = w / self.imgsz
        scale_y = h / self.imgsz
        for name, info in final_13.items():
            b = info["box"]
            x1, y1, x2, y2 = map(float, b.tolist())
            x1_orig = x1 * scale_x
            y1_orig = y1 * scale_y
            x2_orig = x2 * scale_x
            y2_orig = y2 * scale_y
            joints[name] = {
                "type": name,
                "score": round(float(info["score"]), 4),
                "bbox_xyxy": [
                    round(x1_orig, 2),
                    round(y1_orig, 2),
                    round(x2_orig, 2),
                    round(y2_orig, 2),
                ],
                "bbox_space": "original",
                "coord": [
                    round((x1_orig + x2_orig) / 2.0 / w, 4),
                    round((y1_orig + y2_orig) / 2.0 / h, 4),
                    round((x2_orig - x1_orig) / w, 4),
                    round((y2_orig - y1_orig) / h, 4),
                ],
            }

        plot_image_base64 = self._render_with_plt(img_bgr_orig, joints, hand_side)
        return {
            "hand_side": hand_side,
            "detected_count": len(joints),
            "joints": joints,
            "plot_image_base64": plot_image_base64,
        }


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

DETECTED_JOINT_FALLBACKS = {
    "Radius": ["Ulna"],
    "Ulna": ["Radius"],
    "MCPFirst": ["MCPSecond", "MCPThird"],
    "MCPThird": ["MCPSecond", "MCPFourth", "MCPFifth", "MCPFirst"],
    "MCPFifth": ["MCPFourth", "MCPThird", "MCPSecond"],
    "PIPFirst": ["PIPSecond", "PIPThird"],
    "PIPThird": ["PIPSecond", "PIPFourth", "PIPFifth", "PIPFirst"],
    "PIPFifth": ["PIPFourth", "PIPThird", "PIPSecond"],
    "MIPThird": ["MIPSecond", "MIPFourth", "MIPFifth"],
    "MIPFifth": ["MIPFourth", "MIPThird", "MIPSecond"],
    "DIPFirst": ["DIPSecond", "DIPThird"],
    "DIPThird": ["DIPSecond", "DIPFourth", "DIPFifth", "DIPFirst"],
    "DIPFifth": ["DIPFourth", "DIPThird", "DIPSecond"],
}

FINGER_LABELS_EN = ["First", "Second", "Third", "Fourth", "Fifth"]
FINGER_LABELS_CN = {
    "First": "拇指",
    "Second": "食指",
    "Third": "中指",
    "Fourth": "环指",
    "Fifth": "小指",
}
DPV3_PREFIX_RENAME_CONFIG = {
    "MCP": {
        "source_labels": {"MCPFirst", "MCP"},
        "joint_names": ["MCPFirst", "MCPSecond", "MCPThird", "MCPFourth", "MCPFifth"],
        "expected_count": 5,
    },
    "PIP": {
        "source_labels": {"ProximalPhalanx"},
        "joint_names": ["PIPFirst", "PIPSecond", "PIPThird", "PIPFourth", "PIPFifth"],
        "expected_count": 5,
    },
    "MIP": {
        "source_labels": {"MiddlePhalanx"},
        "joint_names": ["MIPSecond", "MIPThird", "MIPFourth", "MIPFifth"],
        "expected_count": 4,
    },
    "DIP": {
        "source_labels": {"DistalPhalanx"},
        "joint_names": ["DIPFirst", "DIPSecond", "DIPThird", "DIPFourth", "DIPFifth"],
        "expected_count": 5,
    },
}


def _region_center_x(region: Dict) -> float:
    centroid = region.get("centroid", (0.0, 0.0))
    if isinstance(centroid, (list, tuple)) and centroid:
        return float(centroid[0])
    return 0.0


def _region_center_y(region: Dict) -> float:
    centroid = region.get("centroid", (0.0, 0.0))
    if isinstance(centroid, (list, tuple)) and len(centroid) > 1:
        return float(centroid[1])
    return 0.0


def _region_confidence(region: Dict) -> float:
    return float(region.get("confidence", 0.0))


def _region_bbox(region: Dict) -> Tuple[float, float, float, float]:
    bbox = region.get("bbox_coords", [0.0, 0.0, 0.0, 0.0])
    if len(bbox) != 4:
        return 0.0, 0.0, 0.0, 0.0
    return tuple(float(v) for v in bbox)


def _bbox_iou(
    box_a: Tuple[float, float, float, float], box_b: Tuple[float, float, float, float]
) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    denom = area_a + area_b - inter_area
    if denom <= 0:
        return 0.0
    return inter_area / denom


def _dedupe_regions_by_overlap(
    regions: List[Dict], expected_count: int, iou_threshold: float = 0.35
) -> List[Dict]:
    if not regions:
        return []

    ordered_by_conf = sorted(
        regions,
        key=lambda item: (
            _region_confidence(item),
            _region_bbox(item)[2] - _region_bbox(item)[0],
        ),
        reverse=True,
    )

    kept: List[Dict] = []
    for region in ordered_by_conf:
        region_box = _region_bbox(region)
        if any(
            _bbox_iou(region_box, _region_bbox(existing)) >= iou_threshold
            for existing in kept
        ):
            continue
        kept.append(region)

    if len(kept) > expected_count:
        kept = kept[:expected_count]

    return kept


def _order_regions_by_hand_side(regions: List[Dict], hand_side: str) -> List[Dict]:
    ordered = sorted(regions, key=_region_center_x)
    if hand_side == "left":
        ordered.reverse()
    return ordered


def _joint_name_to_finger(joint_name: str) -> str:
    for finger in FINGER_LABELS_EN:
        if joint_name.endswith(finger):
            return finger
    return "Wrist"


def _build_named_joint_payload(
    region: Dict, joint_name: str, image_shape: Tuple[int, int], order: int
) -> Dict:
    img_h, img_w = image_shape
    label = region.get("label", "Unknown")
    label_cn = region.get("label_cn", label)
    x1, y1, x2, y2 = _region_bbox(region)
    finger = _joint_name_to_finger(joint_name)
    finger_cn = FINGER_LABELS_CN.get(finger, "腕骨")

    return {
        "type": label_cn,
        "label": joint_name,
        "yolo_label": label,
        "finger": finger,
        "finger_cn": finger_cn,
        "order": order,
        "score": round(_region_confidence(region), 4),
        "bbox_xyxy": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
        "bbox_space": "original",
        "source": region.get("source", "unknown"),
        "coord": [
            round(_region_center_x(region) / img_w, 4) if img_w else 0.0,
            round(_region_center_y(region) / img_h, 4) if img_h else 0.0,
            round((x2 - x1) / img_w, 4) if img_w else 0.0,
            round((y2 - y1) / img_h, 4) if img_h else 0.0,
        ],
    }


def _resolve_hand_side_from_regions(
    regions: List[Dict], fallback: str = "unknown"
) -> str:
    radius_regions = [region for region in regions if region.get("label") == "Radius"]
    ulna_regions = [region for region in regions if region.get("label") == "Ulna"]
    if radius_regions and ulna_regions:
        radius_region = max(radius_regions, key=_region_confidence)
        ulna_region = max(ulna_regions, key=_region_confidence)
        return _resolve_hand_side(
            _region_center_x(radius_region),
            _region_center_x(ulna_region),
            fallback=fallback,
        )
    return fallback if fallback in {"left", "right"} else "unknown"


def rename_dpv3_regions_to_named_joints(
    regions: List[Dict],
    image_shape: Tuple[int, int],
    hand_side_hint: str = "unknown",
) -> Tuple[Dict[str, Dict], List[Dict], str]:
    img_h, img_w = image_shape
    hand_side = _resolve_hand_side_from_regions(regions, hand_side_hint)
    joints: Dict[str, Dict] = {}
    ordered_joints: List[Dict] = []
    joint_index = 0

    for wrist_label in ["Radius", "Ulna"]:
        wrist_regions = [
            region for region in regions if region.get("label") == wrist_label
        ]
        if not wrist_regions:
            continue
        wrist_region = max(wrist_regions, key=_region_confidence)
        payload = _build_named_joint_payload(
            wrist_region, wrist_label, (img_h, img_w), joint_index
        )
        joints[wrist_label] = payload
        ordered_joints.append(payload)
        joint_index += 1

    for prefix, config in DPV3_PREFIX_RENAME_CONFIG.items():
        prefix_regions = [
            region
            for region in regions
            if region.get("label") in config["source_labels"]
        ]
        if not prefix_regions:
            continue

        deduped_regions = _dedupe_regions_by_overlap(
            prefix_regions, config["expected_count"]
        )
        ordered_regions = _order_regions_by_hand_side(deduped_regions, hand_side)

        for joint_name, region in zip(
            config["joint_names"], ordered_regions[: len(config["joint_names"])]
        ):
            payload = _build_named_joint_payload(
                region, joint_name, (img_h, img_w), joint_index
            )
            joints[joint_name] = payload
            ordered_joints.append(payload)
            joint_index += 1

    return joints, ordered_joints, hand_side


def align_joint_semantics(joint_grades: Dict) -> Dict:
    aligned: Dict[str, Dict] = {}

    for src_joint, payload in joint_grades.items():
        if payload.get("grade_raw", None) is None:
            continue
        if src_joint in RUS_13:
            targets = [src_joint]
        else:
            targets = JOINT_TO_RUS.get(src_joint, [])
        for target_joint in targets:
            aligned[target_joint] = {
                "grade_raw": int(payload.get("grade_raw", 0)),
                "score": float(payload.get("score", 0.0)),
                "status": payload.get("status", "ok"),
                "source_joint": src_joint,
                "imputed": False,
            }

    for rus_joint in RUS_13:
        if rus_joint in aligned:
            continue
        picked = None
        for candidate in FALLBACKS.get(rus_joint, []):
            if candidate in aligned:
                picked = candidate
                break
        if picked is not None:
            aligned[rus_joint] = {
                "grade_raw": aligned[picked]["grade_raw"],
                "score": aligned[picked]["score"] * 0.95,
                "status": "semantic_imputed",
                "source_joint": aligned[picked]["source_joint"],
                "imputed": True,
            }
        else:
            aligned[rus_joint] = {
                "grade_raw": 0,
                "score": 0.0,
                "status": "semantic_default",
                "source_joint": "none",
                "imputed": True,
            }

    return aligned


def semantic_align_missing_joint_grades(joint_grades: Dict) -> Dict:
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
        picked_name = None
        for candidate in FALLBACKS.get(joint, []):
            candidate_payload = aligned.get(candidate)
            if candidate_payload and candidate_payload.get("grade_raw", None) is not None:
                picked = candidate_payload
                picked_name = candidate
                break

        if picked is None:
            base = payload if isinstance(payload, dict) else {}
            aligned[joint] = {
                "model_joint": base.get("model_joint", None),
                "grade_idx": None,
                "grade_raw": 0,
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
            "grade_raw": int(picked.get("grade_raw", 0)),
            "score": round(base_score * 0.95, 4),
            "status": "semantic_imputed",
            "imputed": True,
            "source_joint": picked_name,
        }

    return aligned


def standardize_detected_joints_to_rus(
    detected_joints: Dict[str, Dict],
) -> Dict[str, Dict]:
    if not detected_joints:
        return {}

    standardized: Dict[str, Dict] = {}
    for rus_joint in RUS_13:
        if rus_joint in detected_joints:
            standardized[rus_joint] = {
                **detected_joints[rus_joint],
                "standard_joint": rus_joint,
                "source_joint": rus_joint,
                "imputed": False,
            }
            continue

        picked_name = None
        for candidate in DETECTED_JOINT_FALLBACKS.get(rus_joint, []):
            if candidate in detected_joints:
                picked_name = candidate
                break

        if picked_name is None:
            continue

        standardized[rus_joint] = {
            **detected_joints[picked_name],
            "standard_joint": rus_joint,
            "source_joint": picked_name,
            "imputed": True,
        }

    return standardized


def run_joint_assessment_pipeline(
    image_bytes: bytes,
    gender_lower: str,
    *,
    joint_grader: Any,
    joint_recognizer: Any,
    dpv3_detector: Any,
    joint_detection_canvas_size: int,
    joint_model_input_size: int,
    imagenet_mean: np.ndarray,
    imagenet_std: np.ndarray,
    use_dpv3: bool = False,
) -> Dict[str, Any]:
    recognized_joints_13: Dict[str, Any] = {
        "hand_side": "unknown",
        "detected_count": 0,
        "joints": {},
        "plot_image_base64": None,
        "dpv3_enhanced": False,
        "dpv3_info": None,
    }

    if use_dpv3 and dpv3_detector:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_bgr is not None:
                dpv3_results = dpv3_detector.detect(img_bgr, target_count=21)
                if dpv3_results.get("success"):
                    recognized_joints_13["dpv3_enhanced"] = True

                    radius_region = None
                    ulna_region = None
                    for region in dpv3_results.get("regions", []):
                        label = region.get("label", "Unknown")
                        if label == "Radius":
                            radius_region = region
                        elif label == "Ulna":
                            ulna_region = region

                    if radius_region and ulna_region:
                        radius_x = radius_region.get("centroid", (0, 0))[0]
                        ulna_x = ulna_region.get("centroid", (0, 0))[0]
                        hand_side = _resolve_hand_side(
                            radius_x,
                            ulna_x,
                            fallback=dpv3_results.get("hand_side", "unknown"),
                        )
                    else:
                        hand_side = dpv3_results.get("hand_side", "unknown")

                    joints, ordered_joints, hand_side = (
                        rename_dpv3_regions_to_named_joints(
                            dpv3_results.get("regions", []),
                            img_bgr.shape[:2],
                            hand_side,
                        )
                    )

                    recognized_joints_13["dpv3_info"] = {
                        "hand_side": hand_side,
                        "total_regions": dpv3_results.get("total_regions"),
                        "yolo_count": dpv3_results.get("yolo_count"),
                        "bfs_count": dpv3_results.get("bfs_count"),
                        "best_gray_range": dpv3_results.get("best_gray_range"),
                        "merged_blocks": dpv3_results.get("merged_blocks"),
                    }
                    recognized_joints_13["detected_count"] = len(joints)
                    recognized_joints_13["hand_side"] = hand_side
                    recognized_joints_13["joints"] = joints
                    recognized_joints_13["ordered_joints"] = ordered_joints
                    recognized_joints_13["finger_order"] = (
                        FINGER_LABELS_EN
                        if hand_side == "left"
                        else list(reversed(FINGER_LABELS_EN))
                    )
                    recognized_joints_13["rus_13_joints"] = (
                        standardize_detected_joints_to_rus(joints)
                    )
                    print(
                        f"✅ DP V3 enhanced detection: {recognized_joints_13['detected_count']} bones detected"
                    )
        except Exception as dpv3_exc:
            print(f"DP V3 detection failed: {dpv3_exc}")
            traceback.print_exc()

    if not recognized_joints_13.get("dpv3_enhanced"):
        if joint_recognizer:
            try:
                recognized_joints_13 = joint_recognizer.recognize_13(image_bytes)
                recognized_joints_13["dpv3_enhanced"] = False
                recognized_joints_13["dpv3_info"] = None
            except Exception as rec_exc:
                print(f"Small joint recognize failed: {rec_exc}")

        recognized_joints_13.setdefault("hand_side", "unknown")
        recognized_joints_13.setdefault("detected_count", 0)
        recognized_joints_13.setdefault("joints", {})
        recognized_joints_13.setdefault("plot_image_base64", None)

    joint_grades: Dict[str, Any] = {}
    if joint_grader:
        try:
            joint_grades = joint_grader.predict_detected_joints(
                image_bytes,
                recognized_joints_13.get("joints", {}),
                joint_detection_canvas_size,
                joint_model_input_size,
                imagenet_mean,
                imagenet_std,
            )
        except Exception as joint_exc:
            print(f"Joint grading failed: {joint_exc}")

    joint_grades = semantic_align_missing_joint_grades(joint_grades)

    joint_semantic_13: Dict[str, Any] = {}
    joint_rus_total_score = None
    joint_rus_details: List[Dict[str, Any]] = []
    rus_bone_age_years = None
    if joint_grades:
        joint_semantic_13 = align_joint_semantics(joint_grades)
        joint_rus_total_score, joint_rus_details = calc_rus_score_util(
            joint_semantic_13, gender_lower
        )
        if joint_rus_total_score is not None and (
            math.isnan(joint_rus_total_score) or math.isinf(joint_rus_total_score)
        ):
            joint_rus_total_score = 0.0
        if joint_rus_total_score is not None:
            rus_bone_age_years = calc_bone_age_from_score(
                joint_rus_total_score, gender_lower
            )

    if joint_recognizer and joint_grades:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img_bgr_orig = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_bgr_orig is not None:
                new_plot = joint_recognizer._render_with_plt(
                    img_bgr_orig,
                    recognized_joints_13.get("joints", {}),
                    recognized_joints_13.get("hand_side", "unknown"),
                    grades=joint_grades,
                )
                if new_plot:
                    recognized_joints_13["plot_image_base64"] = new_plot
        except Exception as plot_exc:
            print(f"Re-rendering plot with grades failed: {plot_exc}")
            traceback.print_exc()

    recognized_joints_13["rus_13_joints"] = standardize_detected_joints_to_rus(
        recognized_joints_13.get("joints", {})
    )

    return {
        "joint_detect_13": recognized_joints_13,
        "joint_grades": joint_grades,
        "joint_semantic_13": joint_semantic_13,
        "joint_rus_total_score": joint_rus_total_score,
        "joint_rus_details": joint_rus_details,
        "rus_bone_age_years": rus_bone_age_years,
        "detection_algorithm": "dpv3"
        if recognized_joints_13.get("dpv3_enhanced")
        else "yolo",
    }
