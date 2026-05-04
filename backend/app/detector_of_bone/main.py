import base64
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import onnxruntime
import torch


class FractureDetector:
    def __init__(self, model_path: str, device: Optional[str] = None):
        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if (device == "cuda" or (device is None and torch.cuda.is_available()))
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

    def _preprocess(self, image_bytes: bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_orig = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_orig is None:
            return None, None

        img_640 = cv2.resize(img_orig, (640, 640), interpolation=cv2.INTER_LINEAR)
        ok, buf = cv2.imencode(".jpg", img_640)
        detection_image_base64 = None
        if ok:
            detection_image_base64 = "data:image/jpeg;base64," + base64.b64encode(
                buf
            ).decode("utf-8")

        img = cv2.cvtColor(img_640, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, 0)
        img = np.ascontiguousarray(img)

        return img, detection_image_base64

    def detect(
        self, image_bytes: bytes, score_threshold: float = 0.3
    ) -> Tuple[List[Dict], Optional[str]]:
        img_input, detection_image_base64 = self._preprocess(image_bytes)
        if img_input is None:
            return [], None

        outputs = self.session.run([self.output_name], {self.input_name: img_input})[0]
        if len(outputs.shape) == 3:
            outputs = outputs[0]

        anomalies = []
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
