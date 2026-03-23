import uvicorn
import os
import sys

# 处理 PyInstaller 打包后的路径问题
if getattr(sys, 'frozen', False):
    # 打包后的路径
    base_path = sys._MEIPASS
else:
    # 正常运行路径
    base_path = os.path.abspath(".")

# 将项目根目录添加到 python 路径
sys.path.append(base_path)

if __name__ == "__main__":
    from app.main import app
    print("正在启动后端服务...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
