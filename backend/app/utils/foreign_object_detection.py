from typing import Any, Dict, List, Optional

ANOMALY_SCORE_THRESHOLD = 0.3
FOREIGN_OBJECT_SCORE_THRESHOLD = 0.45
FOREIGN_OBJECT_TYPES = {"foreignbody", "metal"}
FOREIGN_OBJECT_MESSAGE = (
    "\u68c0\u6d4b\u5230\u5f02\u7269\uff0c\u53ef\u80fd\u5f71\u54cd\u9aa8\u9f84\u5224\u65ad\uff0c"
    "\u8bf7\u7ed3\u5408\u539f\u59cb\u5f71\u50cf\u590d\u6838"
)


def build_foreign_object_detection(anomalies: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []

    for anomaly in anomalies or []:
        if not isinstance(anomaly, dict):
            continue

        try:
            score = float(anomaly.get("score", 0))
        except (TypeError, ValueError):
            continue

        anomaly_type = str(anomaly.get("type", "")).strip().lower()
        if score < FOREIGN_OBJECT_SCORE_THRESHOLD or anomaly_type not in FOREIGN_OBJECT_TYPES:
            continue

        coord = anomaly.get("coord", [])
        items.append(
            {
                "type": anomaly_type,
                "score": round(score, 3),
                "coord": coord if isinstance(coord, list) else [],
            }
        )

    return {
        "detected": bool(items),
        "count": len(items),
        "threshold": FOREIGN_OBJECT_SCORE_THRESHOLD,
        "message": FOREIGN_OBJECT_MESSAGE if items else None,
        "items": items,
    }
