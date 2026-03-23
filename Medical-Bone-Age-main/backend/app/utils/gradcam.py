import cv2
import numpy as np
import torch
import torch.nn.functional as F

class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        
        # Hooks
        self.target_layer.register_forward_hook(self.save_activation)
        self.target_layer.register_full_backward_hook(self.save_gradient)

    def save_activation(self, module, input, output):
        self.activations = output

    def save_gradient(self, module, grad_input, grad_output):
        # grad_output is a tuple
        self.gradients = grad_output[0]

    def __call__(self, x, gender_input=None):
        # 1. Forward pass
        # Note: We need gradients here, so model must not be in no_grad (partially)
        # But we can assume inputs require_grad=True? No, usually model parameters.
        # Evaluation mode is fine, but we need to run backward()
        
        output = self.model(x, gender_input)
        
        # 2. Backward pass
        # Zero grads
        self.model.zero_grad()
        
        # Target: the predicted score (scalar)
        score = output[0]
        score.backward(retain_graph=True)
        
        # 3. Compute CAM
        # Global Average Pooling of gradients
        gradients = self.gradients
        activations = self.activations
        
        # Shape: (Batch, Channel, H, W) -> (1, 512, 16, 16) approx
        b, k, u, v = gradients.size()
        
        # Mean gradient per channel
        alpha = gradients.view(b, k, -1).mean(2)
        
        # Weighted sum of activations
        weights = alpha.view(b, k, 1, 1)
        cam = (weights * activations).sum(1, keepdim=True)
        
        # ReLU
        cam = F.relu(cam)
        
        # Resize to input image size (500x500)
        # Assuming x is (1, 1, 500, 500)
        cam = F.interpolate(cam, size=(500, 500), mode='bilinear', align_corners=False)
        
        # Normalize to 0-1
        cam = cam - cam.min()
        cam = cam / (cam.max() + 1e-7)
        
        return output, cam.detach().cpu().numpy()[0, 0]

def overlay_heatmap(img_tensor, cam_map):
    """
    img_tensor: torch.Tensor, shape (1,C,H,W) / (C,H,W) / (H,W)
    cam_map: np.ndarray, shape (H,W), value in [0,1]
    return: BGR uint8 image
    """
    # tensor -> numpy
    if hasattr(img_tensor, "detach"):
        img = img_tensor.detach().cpu().numpy()
    else:
        img = np.asarray(img_tensor)

    # 去 batch 维
    if img.ndim == 4:
        img = img[0]  # (C,H,W)

    # CHW -> HWC
    if img.ndim == 3 and img.shape[0] in (1, 3):
        img = np.transpose(img, (1, 2, 0))  # (H,W,C)

    img = img.astype(np.float32)
    img = img - img.min()
    img = img / (img.max() + 1e-7)
    img = (img * 255).astype(np.uint8)

    # 统一到 BGR
    if img.ndim == 2:
        img_color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.ndim == 3 and img.shape[2] == 1:
        img_color = cv2.cvtColor(img[:, :, 0], cv2.COLOR_GRAY2BGR)
    elif img.ndim == 3 and img.shape[2] == 3:
        img_color = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        raise ValueError(f"Unexpected image shape: {img.shape}")

    cam_map = cv2.resize(cam_map, (img_color.shape[1], img_color.shape[0]))
    cam_map = np.clip(cam_map, 0, 1)

    heatmap = (cam_map * 255).astype(np.uint8)
    heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

    superimposed = cv2.addWeighted(heatmap, 0.4, img_color, 0.6, 0)
    return superimposed