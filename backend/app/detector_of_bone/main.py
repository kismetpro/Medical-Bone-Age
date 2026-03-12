import numpy as np
import cv2
import onnxruntime


class FractureDetector:
    def __init__(self, model_path, device="cpu"):
        providers = ['CUDAExecutionProvider'] if device == "cuda" else ['CPUExecutionProvider']
        # 加入异常处理，防止模型路径错误
        try:
            self.session = onnxruntime.InferenceSession(model_path, providers=providers)
        except Exception as e:
            print(f"模型加载失败: {e}")
            raise

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        self.id2names = {
            0: "boneanomaly", 1: "bonelesion", 2: "foreignbody",
            3: "fracture", 4: "metal", 5: "periostealreaction",
            6: "pronatorsign", 7: "softtissue", 8: "text"
        }

    def _preprocess(self, image_bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_orig = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_orig is None:
            return None, (0, 0)

        h_orig, w_orig = img_orig.shape[:2]

        # 保持比例的 Resize (Letterbox) 虽然更好，但如果你之前的训练是直接 Resize，这里保持一致
        img = cv2.cvtColor(img_orig, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (640, 640))
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, 0)

        return img, (h_orig, w_orig)

    def detect(self, image_bytes, score_threshold=0.3):
        img_input, (H, W) = self._preprocess(image_bytes)
        if img_input is None: return []

        # 推理
        outputs = self.session.run([self.output_name], {self.input_name: img_input})

        # 关键修正：有些 ONNX 返回 [1, N, 6]，有些返回 [N, 6]
        output = np.array(outputs[0])
        if len(output.shape) == 3:
            output = output[0]

        anomalies = []
        for det in output:
            # 兼容性处理：有些模型输出是 [x1, y1, x2, y2, obj_conf, cls_conf, label]
            # 这里假设你的模型已经内置了 NMS 并输出 [x1, y1, x2, y2, score, label]
            if len(det) < 6: continue

            score = float(det[4])
            if score > score_threshold:
                # 坐标裁剪：防止坐标超出 640 范围
                x1 = max(0, min(640, det[0]))
                y1 = max(0, min(640, det[1]))
                x2 = max(0, min(640, det[2]))
                y2 = max(0, min(640, det[3]))

                # 计算归一化坐标
                norm_xc = round(((x1 + x2) / 2) / 640.0, 4)
                norm_yc = round(((y1 + y2) / 2) / 640.0, 4)
                norm_w = round((x2 - x1) / 640.0, 4)
                norm_h = round((y2 - y1) / 640.0, 4)

                label_id = int(det[5])
                anomalies.append({
                    "type": self.id2names.get(label_id, f"unknown_{label_id}"),
                    "score": round(score, 3),
                    "coord": [norm_xc, norm_yc, norm_w, norm_h]
                })

        return anomalies