"""
第1轮优化：改进可视化，用矩形框标记关节
==========================================

优化目标：
1. 使用最小外接矩形（带旋转）框出关节
2. 用最长边作为矩形框的主要尺寸
3. 在框内标注关节名称、面积、扫描顺序

主要改进：
- 可视化函数使用cv2.minAreaRect()获取最小外接矩形
- 显示框的中心坐标
- 标注更多信息（名称、面积、顺序）
"""

import cv2
import numpy as np


def visualize_with_rotated_rect(vis, mask, label, color, region_info):
    """绘制最小外接矩形"""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return vis
    
    contour = contours[0]
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    cv2.drawContours(vis, [box], 0, color, 2)
    
    rect_w, rect_h = rect[1]
    max_side = max(rect_w, rect_h)
    min_side = min(rect_w, rect_h)
    rect_center = (int(rect[0][0]), int(rect[0][1]))
    
    info_text = f"{label}"
    area_text = f"W:{max_side:.0f} H:{min_side:.0f}"
    order_text = f"#{region_info.get('order', 0)}"
    
    cv2.putText(vis, info_text, 
                (rect_center[0] - 30, rect_center[1] - 15), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    cv2.putText(vis, area_text, 
                (rect_center[0] - 30, rect_center[1] + 5), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(vis, order_text, 
                (rect_center[0] - 30, rect_center[1] + 25), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)
    
    return vis


if __name__ == "__main__":
    print("\n" + "="*70)
    print("第1轮优化：改进可视化，用矩形框标记关节")
    print("="*70)
    print("""
优化内容：
1. 使用cv2.minAreaRect()获取最小外接矩形（带旋转）
2. 用最长边作为矩形框的主要尺寸
3. 在框内标注：
   - 关节名称
   - 矩形框宽高（最长边/最短边）
   - 扫描顺序

预计效果：
✅ 更精确地框出关节区域
✅ 适应不同角度的关节
✅ 提供更多信息供调试
    """)
