"""
生成传统CV与YOLO方法对比可视化
"""

import cv2
import os


def create_comparison_visualization():
    """创建对比图"""
    
    # 读取两张结果图
    trad_cv_path = "scanning_rotation_result_check_this_image.jpg"
    yolo_path = "yolo_result_check_this_image.jpg"
    
    if not os.path.exists(trad_cv_path):
        print(f"❌ 传统CV结果图不存在: {trad_cv_path}")
        return
    
    if not os.path.exists(yolo_path):
        print(f"❌ YOLO结果图不存在: {yolo_path}")
        return
    
    # 读取图像
    trad_cv = cv2.imread(trad_cv_path)
    yolo = cv2.imread(yolo_path)
    
    if trad_cv is None or yolo is None:
        print("❌ 无法读取图像")
        return
    
    # 调整到相同尺寸
    h, w = trad_cv.shape[:2]
    yolo_resized = cv2.resize(yolo, (w, h))
    
    # 创建并排对比图
    comparison = cv2.hconcat([trad_cv, yolo_resized])
    
    # 添加标题
    h_new = h + 60
    comparison_padded = cv2.copyMakeBorder(
        comparison,
        60, 0, 0, 0,
        cv2.BORDER_CONSTANT,
        value=(255, 255, 255)
    )
    
    # 添加标题文字
    cv2.putText(comparison_padded, "Traditional CV (8 bones)", 
               (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(comparison_padded, "YOLO (21 bones)", 
               (w + 10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(comparison_padded, "BONE DETECTION COMPARISON", 
               (w - 200, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    
    # 保存对比图
    output_path = "bone_detection_comparison.jpg"
    cv2.imwrite(output_path, comparison_padded)
    print(f"✅ 对比图已保存: {output_path}")
    
    return output_path


if __name__ == "__main__":
    create_comparison_visualization()
