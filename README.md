# Medical-Bone-Age 🦴

医疗骨龄识别与管理系统 - 前后端分离项目。

## 🚀 开发者部署教程

按照以下步骤在本地环境中安装并运行项目。

### 1. 模型文件配置

由于模型文件体积较大，项目中的权重及模型文件通过压缩包形式提供，请务必完成以下解压操作：

- 将 **weight 压缩包**的内容解压到目录：`backend\app\detector_of_bone`
- 将 **models 压缩包**的内容解压到目录：`backend\app`

### 2. 前端依赖配置

1. 打开终端，进入前端目录：
   ```bash
   cd .\frontend\
   ```
2. 安装必要的依赖包：
   ```bash
   npm install
   ```

### 3. 后端依赖配置

1. 在终端中切换到后端目录：
   ```bash
   cd .\backend\
   ```
2. 使用以下命令安装 Python 依赖项：
   ```bash
   python -m pip install -r requirements.txt
   ```

### 4. 运行项目

请确保后端先启动，然后再运行前端。

- **运行后端**：
  进入 `backend` 文件夹，执行：
  ```bash
  python .\entry_point.py
  ```
- **运行前端**：
  进入 `frontend` 文件夹，执行：
  ```bash
  npm run dev
  ```

### 5. 访问项目

在浏览器中打开以下地址：
[http://localhost:5173/](http://localhost:5173/)

> [!IMPORTANT]
> **注意**：由于数据库、缓存（如图片、记录等）已同步上传，建议您手动注册并创建一个自己能记住的账号密码进行登录使用。

---

## 🛠️ GitHub Desktop 使用教程

如果您使用 GitHub Desktop 进行版本控制，请参考以下指南：

### 1. 软件安装
- 下载并安装 [Git](https://git-scm.com/)。
- 下载并安装 [GitHub Desktop](https://desktop.github.com/)。

### 2. 克隆仓库
- 登录 GitHub 账号后，点击克隆仓库（Clone a repository）。
- 选择 **URL** 选项。
- 填写仓库地址：`https://github.com/kismetpro/Medical-Bone-Age.git`。

### 3. 提交代码流程
- 在提交代码时，必须在 **Summary** 栏填写简要的改动说明。
- 点击 **Commit to main**。
- **重要建议**：在提交之前，务必先在本地环境进行完整测试。确认运行正常后再进行提交。

### 4. 撤回提交 (Revert)
如果提交后发现错误需要撤销：
- 在 **History** 选项卡中，找到你想撤回的提交（必须是最近的一个）。
- 右键点击该提交，选择 **Revert changes in commit**。

## 👤 使用示例

### 启动项目
点击 `start.bat` 等待网页出现

### 账号使用
内置了三个账号
- admin-Admin123456 超级管理员，拥有额外管理账号的权利
- doctor-Doctor123456 临床医生，正常的医生功能
- user-User123456 个人用户，正常的用户功能

---

感谢使用 Medical-Bone-Age 项目！如有任何疑问，请参考项目文档或联系开发团队。
doctor
Doctor123456