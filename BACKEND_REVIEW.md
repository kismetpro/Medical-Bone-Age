# 后端代码审查报告 — 解耦合与潜在 Bug

**范围**：`backend/app/**`（FastAPI + PyTorch + ONNX + SQLite），以 [backend/app/main.py](backend/app/main.py)（4128 行）为主。
**审查日期**：2026-04-23
**关注点**：模块耦合 / 可维护性 / 潜在运行时 Bug / 安全与并发

---

## 0. TL;DR 优先级落地顺序

| 优先级 | 类别 | 项目 | 风险 |
|---|---|---|---|
| P0 立刻 | 安全 | [A](#bug-a-send_notification-无鉴权) `/send_notification` 无鉴权 | 被当作免费 SMTP/Webhook 中继 |
| P0 立刻 | 安全 | [D](#bug-d-启动时强制重置内置账户密码) 启动即重置内置账户密码 | 密码回滚、所有用户被踢 |
| P0 立刻 | 可用性 | [J](#bug-j-ai-流式代理阻塞事件循环) / [解耦 8](#解耦-8-async-路由里做阻塞-io) 异步路由中阻塞事件循环 | 单请求卡死整个 worker |
| P0 立刻 | 安全 | [F](#bug-f-内存限流是单进程且无上限) 限流内存化 + 无上限 | 多 worker 下失效，字典无限增长 |
| P1 一周 | 可用性 | [B](#bug-b-jointgraderpredict-是坏代码) `JointGrader.predict` 坏代码 | 走到分支即崩 |
| P1 一周 | 可用性 | [C](#bug-c-gradcam-并发竞态) GradCAM 并发竞态 | 并发请求输出错乱/异常 |
| P1 一周 | 性能 | [E](#bug-e-每次鉴权都写库) 每次鉴权都 DELETE | SQLite 写锁放大 |
| P1 一周 | 正确性 | [G](#bug-g-hand_side-方向判定在三处不一致) `hand_side` 三处判定不一致 | 左右手/手指顺序错 |
| P1 一周 | 并发 | [H](#bug-h-matplotlib-pyplot-线程不安全) matplotlib pyplot 非线程安全 | 偶发 PNG 损坏 |
| P2 迭代 | 解耦 | [解耦 2/3](#解耦-2-score_table-被复制两份) 重复代码删除 | 长期维护负担 |
| P2 迭代 | 解耦 | [解耦 1/4/5/6](#解耦-1-mainpy-是单体巨文件) `main.py` 拆分 + 配置集中 + DI | 可测试性 |
| P2 迭代 | 解耦 | [解耦 9](#解耦-9-邮件通知通过子进程调用) 邮件去 subprocess | 稳定性/性能 |
| P3 后续 | 正确性 | K–T 细节健壮性 | 见下 |

---

## 一、解耦合问题

### 解耦 1. `main.py` 是单体巨文件

**位置**：[backend/app/main.py](backend/app/main.py) 共 4128 行。
**现状**：同一个文件内混杂：模型类（`BoneAgeModel`/`JointClassifier`/`DANNHyperModel`/`JointGrader`/`FractureDetector`/`SmallJointRecognizer`）、常量（`SCORE_TABLE`/`RUS_13`/`JOINT_TO_RUS`/`FALLBACKS`）、Auth 数据库 Schema & 迁移、密码/会话/限流、40+ HTTP 路由、图像预处理、Grad-CAM 编排、DeepSeek SSE 代理。

**解决方法**：按领域拆分，用 FastAPI 的 `APIRouter` 组合：

```
backend/app/
├── main.py                    # 仅 FastAPI 实例 + lifespan + include_router
├── config.py                  # pydantic BaseSettings（见解耦 4）
├── deps.py                    # Depends: get_session, require_doctor, ...
├── db/
│   ├── auth_repo.py           # users / sessions / qa / articles
│   └── prediction_repo.py     # predictions / bone_age_points
├── schemas/
│   ├── auth.py  predictions.py  qa.py  notifications.py
├── routers/
│   ├── auth.py  predictions.py  bone_age_points.py  qa.py
│   ├── articles.py  notifications.py  ai_assistant.py
├── services/
│   ├── age_inference.py       # ensemble TTA + gradcam
│   ├── joint_grading.py       # 统一封装 YOLO / DPV3 / 手绘 三条路径
│   └── notification.py        # smtplib / httpx webhook
└── models/                    # 纯 nn.Module 定义
    ├── bone_age.py  joint_dann.py  fracture.py  small_joint.py
```

骨架示例：
```python
# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers import auth, predictions, bone_age_points, qa, articles, notifications, ai_assistant
from app.services.registry import ModelRegistry

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.models = ModelRegistry.load()
    yield
    app.state.models.close()

app = FastAPI(lifespan=lifespan)
for r in (auth.router, predictions.router, bone_age_points.router,
          qa.router, articles.router, notifications.router, ai_assistant.router):
    app.include_router(r)
```

---

### 解耦 2. `SCORE_TABLE` 被复制两份

**位置**：[main.py:914-945](backend/app/main.py#L914) 与 [utils/rus_chn.py:4-35](backend/app/utils/rus_chn.py#L4)。
**风险**：数据静默漂移。任何一处修改，另一处仍为旧值，RUS 评分将得出不同结果。

**解决方法**：删除 main.py 中的副本，统一从 `utils.rus_chn` 导入：

```python
# main.py 顶部
from app.utils.rus_chn import SCORE_TABLE, calc_bone_age_from_score, generate_bone_report
```
并删除 [main.py:914-945](backend/app/main.py#L914)。建议给 `rus_chn` 再导出 `BONE_NAMES_CN`、`RUS_13` 常量，让"数据定义"与"业务逻辑"分离。

---

### 解耦 3. `FractureDetector` 被复制两份

**位置**：[main.py:384-449](backend/app/main.py#L384) 与 [detector_of_bone/main.py:6-81](backend/app/detector_of_bone/main.py#L6)。
**现状**：`detector_of_bone/main.py` 从未被 `import`。

**解决方法**：删除 `detector_of_bone/main.py`（或保留模型权重目录但删掉代码），唯一实现放在 `app/models/fracture.py`：

```python
# app/models/fracture.py  — 从 main.py 抽取
class FractureDetector: ...
```
然后 main.py `from app.models.fracture import FractureDetector`。

---

### 解耦 4. 配置散落在 main.py 顶层

**位置**：[main.py:1174-1215](backend/app/main.py#L1174) 一大串 `os.getenv(...)`。`config.py` 存在但只放邮件模板。

**解决方法**：集中到 `Settings`：

```python
# app/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    model_config = {"env_file": Path(__file__).resolve().parent.parent / ".env"}

    auth_db_path: str = "app/data/auth.db"
    prediction_db_path: str = "app/data/predictions.db"
    auth_token_expire_hours: int = 24
    pbkdf2_iterations: int = 210_000
    doctor_register_key: str = ""
    doctor_self_register_enabled: bool = False
    super_admin_init_password: str = ""
    auth_cookie_name: str = "boneage_session"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    allowed_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    allowed_origin_regex: str = r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$"
    allowed_hosts: list[str] = ["127.0.0.1", "localhost"]
    auth_rate_limit_window_seconds: int = 300
    auth_rate_limit_max_attempts: int = 10
    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    fracture_model_path: str = "app/detector_of_bone/weight/yolov7-p6-bonefracture.onnx"
    joint_model_dir: str = "app/models/joints"
    joint_recognize_model_path: str = "app/models/recognize/best.pt"

settings = Settings()
```
路由/服务只 `from app.config import settings`。

---

### 解耦 5. 模型通过模块级全局量访问

**位置**：[main.py:1234-1238](backend/app/main.py#L1234)、多处 `global` 与 `if not models_ensemble:`。
**风险**：测试 mock 困难；PyInstaller 冻结或多 worker 部署下，全局隐式状态不清晰；循环 import 风险。

**解决方法**：挂到 `app.state` 或依赖注入容器：

```python
# app/services/registry.py
from dataclasses import dataclass
@dataclass
class ModelRegistry:
    ensemble: list
    fracture: "FractureDetector | None"
    grader: "JointGrader | None"
    recognizer: "SmallJointRecognizer | None"
    dpv3: "DPV3BoneDetector | None"
    @classmethod
    def load(cls) -> "ModelRegistry": ...
    def close(self): ...

# app/deps.py
from fastapi import Request
def get_models(request: Request) -> ModelRegistry:
    return request.app.state.models
```
路由函数 `def predict(..., models: ModelRegistry = Depends(get_models))` 即可，便于 pytest 注入 mock。

---

### 解耦 6. `/predict`、`/joint-grading`、`/joint-dpv3-detect`、`/formula-calculation` 大量重复逻辑

**位置**：[main.py:2810](backend/app/main.py#L2810)、[3610](backend/app/main.py#L3610)、[3800](backend/app/main.py#L3800)、[3937](backend/app/main.py#L3937)。四处都有"识别 → 分级 → 语义对齐 → RUS → 绘图"的重复管线。

**解决方法**：抽 `JointGradingService`：

```python
# app/services/joint_grading.py
class JointGradingService:
    def __init__(self, models: ModelRegistry): self.m = models

    def run(self, image_bytes: bytes, gender: str, *, source: str = "yolo",
            manual_joints: dict | None = None) -> dict:
        joints, hand_side = self._detect(image_bytes, source, manual_joints)
        raw_grades = self._grade(image_bytes, joints)
        grades = semantic_align_missing_joint_grades(raw_grades)
        semantic_13 = align_joint_semantics(grades)
        total, details = calc_rus_score(semantic_13, gender)
        bone_age = calc_bone_age_from_score(total, gender) if total else None
        return {...}
```
四个路由各自只负责：**解析输入 → 调 service → 序列化输出**。

---

### 解耦 7. GradCAM 耦合 ResNet 内部结构 + 操作 PyTorch 私有字段

**位置**：[main.py:2031-2057](backend/app/main.py#L2031)：
```python
target = cam_model.backbone.layer4[-1]
...
target._forward_hooks.clear()
target._backward_hooks.clear()
```
直接抓 ResNet 内部 + 写 `_forward_hooks` 私有 dict。（见 [Bug C](#bug-c-gradcam-并发竞态) 的并发问题。）

**解决方法**：把 hook 的注册/移除放进 `GradCAM` 本体，作为上下文管理器，且调用方传显式 target：

```python
# app/utils/gradcam.py
class GradCAM:
    def __init__(self, model, target_layer):
        self.model, self.target = model, target_layer
        self._fh = self._bh = None
    def __enter__(self):
        self._fh = self.target.register_forward_hook(self._save_act)
        self._bh = self.target.register_full_backward_hook(self._save_grad)
        return self
    def __exit__(self, *exc):
        if self._fh: self._fh.remove()
        if self._bh: self._bh.remove()

# 调用
with GradCAM(cam_model, cam_model.backbone.layer4[-1]) as cam:
    _, mask = cam(x, gender)
```

---

### 解耦 8. `async` 路由里做阻塞 I/O

**位置**：`/predict` [2810](backend/app/main.py#L2810)、`/joint-grading` [3610](backend/app/main.py#L3610)、`/doctor/ai-assistant` [3346](backend/app/main.py#L3346)、`/user/ai-consult*` [3431/3504](backend/app/main.py#L3431)。都是 `async def`，但：
- 内部 `model(...)` 是同步 torch 推理；
- `requests.post(..., stream=True)` 是同步 HTTP。

**解决方法**：
- 推理放到线程池：`await asyncio.to_thread(run_pipeline, content, gender)` 或 FastAPI 的 `fastapi.concurrency.run_in_threadpool`；
- DeepSeek 代理改 `httpx.AsyncClient`：

```python
import httpx
async def generate_stream():
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", api_url, headers=headers, json=body) as r:
            async for line in r.aiter_lines():
                ...
```

---

### 解耦 9. 邮件通知通过子进程调用

**位置**：[utils/notification_service.py:159-175](backend/app/utils/notification_service.py#L159)：每封邮件 `subprocess.run([sys.executable, send_smtp_email.py, ...])`。
**风险**：每封邮件启动一个 Python 解释器；命令行参数传 `--body <长文本>` 在 Windows 有长度限制；外部脚本路径强耦合。

**解决方法**：直接 `smtplib` + `email.message.EmailMessage`：

```python
import smtplib, ssl
from email.message import EmailMessage
from app.config import settings

def send_email_smtp(to: str, subject: str, html_body: str):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.email_sender, to, subject
    msg.set_content("Please view in HTML client.")
    msg.add_alternative(html_body, subtype="html")
    ctx = ssl.create_default_context()
    if settings.email_use_ssl:
        with smtplib.SMTP_SSL(settings.email_smtp_server, settings.email_smtp_port, context=ctx) as s:
            s.login(settings.email_sender, settings.email_password); s.send_message(msg)
    else:
        with smtplib.SMTP(settings.email_smtp_server, settings.email_smtp_port) as s:
            if settings.email_use_tls: s.starttls(context=ctx)
            s.login(settings.email_sender, settings.email_password); s.send_message(msg)
```

---

### 解耦 10. 两个 SQLite DB 都用裸 `sqlite3.connect` 逐请求打开

**位置**：[main.py:1411-1426](backend/app/main.py#L1411)。无连接池、无 WAL、无统一事务上下文。

**解决方法**：最小改动 — 打开即设置 PRAGMA，并集中仓储层：

```python
# app/db/sqlite.py
import sqlite3
def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```
进一步可用 SQLAlchemy Core + `sqlalchemy.create_engine(..., poolclass=QueuePool)`。

---

## 二、潜在 Bug（按风险排序）

### Bug A. `/send_notification` 无鉴权

**位置**：[main.py:2772-2807](backend/app/main.py#L2772)。
```python
@app.post("/send_notification")
async def send_notification(request: NotificationRequest): ...
```
任何匿名客户端都能让服务器向任意 `recipient` 发邮件/企业微信/飞书 webhook，实际上是**免费 SMTP / Webhook 中继**。

**解决方法**：加鉴权并校验 recipient：
```python
@app.post("/send_notification")
async def send_notification(payload: NotificationRequest, request: Request):
    session = _require_doctor(request)          # 或 _require_session，按产品定义
    if payload.method == "email":
        _validate_email(payload.recipient)      # 正则 + 禁止 @internal 域
    else:
        _validate_webhook_url(payload.recipient) # 限制 scheme=https、黑名单 127/10/172.16/192.168
    ...
```

---

### Bug B. `JointGrader.predict` 是坏代码

**位置**：[main.py:285-310](backend/app/main.py#L285)：
```python
x = self.preprocess(image_bytes, img_size, mean, std)   # 返回 torch.Tensor
# x =  image_bytes
x = cv2.resize(x, (1024, 1024))                          # cv2 不接受 Tensor → TypeError
```

**解决方法**：实际被调用的是 `predict_detected_joints`，此 `predict` 已经死代码。直接删除整段即可，避免以后有人调用后崩溃。如果仍需保留"整图分级"的能力，恢复为：
```python
@torch.no_grad()
def predict(self, image_bytes, img_size, mean, std):
    if not self.models: return {}
    x = self.preprocess(image_bytes, img_size, mean, std)
    out = {}
    for joint, item in self.models.items():
        logits, _, _ = item["model"](x, lambda_grl=0.0)
        # ... 原逻辑
    return out
```
（即去掉错误的 `cv2.resize(x, (1024, 1024))` 一行。）

---

### Bug C. GradCAM 并发竞态

**位置**：[main.py:2036-2046](backend/app/main.py#L2036)：
```python
grad_cam = GradCAM(cam_model, target)     # hook 注册到模块级全局模型
...
target._forward_hooks.clear()             # 清掉该 layer 上所有 hook（含并发请求的）
target._backward_hooks.clear()
```
两个并发 `/predict` 共享同一 `target`：双方互相覆盖 `self.activations/self.gradients`；先完成者的 `clear()` 还会抹掉另一者的 hook。

**解决方法**：
1. 用 `handle.remove()`，不要碰 `_forward_hooks` 私有字段（见 [解耦 7](#解耦-7-gradcam-耦合-resnet-内部结构--操作-pytorch-私有字段)）。
2. GradCAM 需要反向传播，无法简单 clone 模型；最直接的兜底是**串行化**：

```python
import asyncio
_gradcam_lock = asyncio.Lock()

async def build_gradcam(...):
    async with _gradcam_lock:
        return await asyncio.to_thread(_gradcam_sync, ...)
```
若需要真并发，考虑复制一份 `cam_model`（或 layer）给每个请求用。

---

### Bug D. 启动时强制重置内置账户密码

**位置**：[main.py:1633-1669 `_ensure_builtin_accounts`](backend/app/main.py#L1633)：
```python
builtin = [("admin", "Admin123456", ROLE_SUPER_ADMIN),
           ("doctor", "Doctor123456", ROLE_DOCTOR),
           ("user",   "User123456",   ROLE_USER)]
# 每次启动对存在的用户做 UPDATE password_hash + DELETE sessions
```
后果：
- 生产上改过这三账户密码的，每次重启都被静默回滚为弱密码；
- 所有会话被踢；
- 同时 [`_ensure_default_super_admin` 1627-1630](backend/app/main.py#L1627) 把临时 super_admin 密码 `print` 到 stdout。

**解决方法**：
1. 删除 `_ensure_builtin_accounts`，或把它收敛成**仅当 users 表为空时**播种一次；
2. 播种后立即在日志里提示"请尽快修改默认密码"，**不要打印密码**；
3. 强制要求通过 `SUPER_ADMIN_INIT_PASSWORD` 环境变量设置，为空则拒绝启动（而不是生成随机密码打印到 stdout）。

```python
def _seed_accounts_if_empty(conn):
    count = conn.execute("SELECT COUNT(1) FROM users").fetchone()[0]
    if count > 0: return
    pwd = settings.super_admin_init_password
    if not _validate_password_strength(pwd):
        raise RuntimeError("SUPER_ADMIN_INIT_PASSWORD required (upper/lower/digit, >=8)")
    # 只创建 super_admin，一次性
    _insert_user(conn, "admin", pwd, ROLE_SUPER_ADMIN)
```

---

### Bug E. 每次鉴权都写库

**位置**：[main.py:1833-1871](backend/app/main.py#L1833)：
```python
def cleanup_expired_sessions(conn):
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_iso,))

def get_session(conn, token):
    cleanup_expired_sessions(conn)   # ← 每个鉴权请求都执行一次 DELETE
    ...
```
每个受保护请求都触发一次写，抢 SQLite 写锁；高 QPS 下成瓶颈。

**解决方法**：去掉 `get_session` 里的 `cleanup_expired_sessions`，改成后台定时或启动时执行：
```python
# app/main.py lifespan
async def _bg_cleanup():
    while True:
        await asyncio.sleep(3600)
        with connect(settings.auth_db_path) as c:
            c.execute("DELETE FROM sessions WHERE expires_at <= ?", (_to_iso(_utc_now()),))

@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(_bg_cleanup())
    yield
    task.cancel()
```
`get_session` 内只检查当前 token 是否过期即可。

---

### Bug F. 内存限流是单进程且无上限

**位置**：[main.py:1875, 1891-1902](backend/app/main.py#L1875)：
```python
_auth_rate_bucket: Dict[str, deque] = {}   # 按 IP 累积，永不裁剪
```
- 多 worker 部署下每 worker 一份字典 → 限流可被 worker 数量倍数绕过；
- 字典 key 按 IP 增长，长寿进程下内存缓慢泄漏。

**解决方法**（选一，按部署规模）：
- **最小改动**：给字典加容量上限 + TTL 淘汰（`cachetools.TTLCache`）：
  ```python
  from cachetools import TTLCache
  _auth_rate_bucket = TTLCache(maxsize=50_000, ttl=settings.auth_rate_limit_window_seconds)
  ```
- **正确方案**：Redis + `INCR key` + `EXPIRE`，多 worker 共享状态。或直接上 `slowapi` / `fastapi-limiter`。

---

### Bug G. `hand_side` 方向判定在三处不一致

| 位置 | 代码 | 等价含义 |
|---|---|---|
| [main.py:550-552](backend/app/main.py#L550) (`recognize_13`) | `is_left = ulna_x < radius_x` | `ulna < radius` ⇒ left |
| [main.py:846-859](backend/app/main.py#L846) (`_resolve_hand_side_from_regions`) | `"left" if radius_x > ulna_x else "right"` | `radius > ulna` ⇒ left ✓ 同上 |
| [main.py:3669-3674](backend/app/main.py#L3669) (`/joint-grading` DPV3 分支) | `if radius_x > ulna_x: "left" else "right"` | `radius > ulna` ⇒ left ✓ |

重读之后：三处其实一致（`radius > ulna` ⇒ left）。**但**三段逻辑独立实现、各自维护，极易在后续修改时劈开。

**解决方法**：抽单一事实源：
```python
# app/services/hand_side.py
def resolve(radius_x: float | None, ulna_x: float | None, fallback: str = "unknown") -> str:
    if radius_x is None or ulna_x is None: return fallback
    return "left" if radius_x > ulna_x else "right"
```
三处全改成调用 `resolve(...)`。同时加 1-2 个单元测试锁定方向。

---

### Bug H. matplotlib pyplot 线程不安全

**位置**：[main.py:458-513 `SmallJointRecognizer._render_with_plt`](backend/app/main.py#L458)。`plt.subplots` / `plt.close` 全局状态在并发请求下可能产生损坏 PNG 或偶发异常。

**解决方法**：使用显式面向对象 API：
```python
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

fig = Figure(figsize=(8, 10), dpi=120)
canvas = FigureCanvasAgg(fig)
ax = fig.add_subplot(111)
# ...绘制...
canvas.draw()
rgba = np.asarray(canvas.buffer_rgba())
# 不需要 plt.close()；fig 引用释放即可
```

---

### Bug I. 上传体积限制时机错

**位置**：`MAX_UPLOAD_IMAGE_BYTES = 20MB` [main.py:1946](backend/app/main.py#L1946)，但 `validate_image_content` 只在 `content = await file.read()` **之后**判长度。
`/qa/questions` 的 `image` base64 字段又允许 ~10M 字符 ≈ 7.5MB 解码后，直接存 auth.db。

**解决方法**：
```python
# 读之前先查 Content-Length
cl = int(request.headers.get("content-length") or 0)
if cl and cl > MAX_UPLOAD_IMAGE_BYTES:
    raise HTTPException(413, "Image file is too large")

# 或流式读
from starlette.requests import Request
async def _read_limited(file, limit=MAX_UPLOAD_IMAGE_BYTES):
    buf, total = bytearray(), 0
    while chunk := await file.read(1024 * 64):
        total += len(chunk)
        if total > limit:
            raise HTTPException(413, "Image file is too large")
        buf.extend(chunk)
    return bytes(buf)
```
QA 图片建议落盘或放 `blob` 表（别塞进 `auth.db`），见 [解耦 10](#解耦-10-两个-sqlite-db-都用裸-sqlite3connect-逐请求打开)。

---

### Bug J. AI 流式代理阻塞事件循环

**位置**：`/doctor/ai-assistant` [3378-3422](backend/app/main.py#L3378)、`/user/ai-consult*` [3450-3494/3536-3581](backend/app/main.py#L3450)：同步 `requests.post(stream=True)` + `resp.iter_lines()` 在 `async` 生成器内迭代。单慢请求卡死整个 worker。

**解决方法**（与 [解耦 8](#解耦-8-async-路由里做阻塞-io) 对应）：
```python
import httpx, json
from fastapi.responses import StreamingResponse

async def stream_deepseek(messages: list[dict], temperature: float):
    url = settings.deepseek_api_base.rstrip("/") + "/chat/completions"
    body = {"model": settings.deepseek_model, "messages": messages,
            "temperature": temperature, "stream": True}
    headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, json=body, headers=headers) as r:
            if r.status_code >= 400:
                text = (await r.aread()).decode("utf-8", "ignore")[:400]
                yield f"data: {json.dumps({'error': text})}\n\n"; return
            async for line in r.aiter_lines():
                if not line.startswith("data: "): continue
                payload = line[6:]
                if payload == "[DONE]": yield "data: [DONE]\n\n"; break
                try:
                    delta = json.loads(payload)["choices"][0].get("delta", {})
                    if (c := delta.get("content")):
                        yield f"data: {json.dumps({'content': c})}\n\n"
                except json.JSONDecodeError: continue
```

---

### Bug K. `/predict` 对无效 token 不返回 401

**位置**：[main.py:2833-2837](backend/app/main.py#L2833)：
```python
token = _resolve_token(request, None)
session_row = None
if token:
    with get_auth_conn() as conn:
        session_row = get_session(conn, token)   # 失败就 None，不抛
```
伪造的 `Authorization: Bearer garbage` 会被静默当作"未登录"继续推理。

**解决方法**：区分"未携带 token"与"token 非法"：
```python
token = _resolve_token(request, None)
session_row = None
if token is not None:
    with get_auth_conn() as conn:
        session_row = get_session(conn, token)
    if session_row is None:
        raise HTTPException(401, "Session expired or invalid")
```

---

### Bug L. `_fit_bone_age_trend` 可能给出误导性 R²

**位置**：[main.py:2587-2640](backend/app/main.py#L2587)。当所有 y 相近，`ss_tot <= 1e-9` 时直接返回 `r2 = 1.0`；当 `point_time` 相同且 `chronological_age_years` 缺失，设计矩阵秩不足但 `lstsq` 给出最小范数解而不抛异常。

**解决方法**：显式判秩：
```python
rank = int(np.linalg.matrix_rank(x))
if rank < x.shape[1]:
    return {"enough": False, "message": "设计矩阵秩不足，至少需要多样的时间或年龄", ...}
if ss_tot <= 1e-9:
    return {"enough": False, "message": "骨龄点几乎无变化", ...}
```

---

### Bug M. `calc_bone_age_from_score(0, ...)` 给出 ~2 岁 / ~5.8 岁

**位置**：[rus_chn.py:63-74](backend/app/utils/rus_chn.py#L63)。多项式常数项导致 score=0 返回非 0。`/manual-grade-calculation` 当全部关节缺失时，`grade_raw=0 → score≈0 → "2 岁"`，会误导用户。

**解决方法**：在 `calc_bone_age_from_score` 入口加最小 score 阈值；或在端点层先校验 `joint_count > 0`：
```python
@app.post("/manual-grade-calculation")
async def manual_grade_calculation(request: ManualGradeRequest):
    provided = {k: v for k, v in request.grades.items() if v is not None and k in RUS_13}
    if not provided:
        raise HTTPException(400, "至少需要一个关节的分级")
    ...
```

---

### Bug N. `predict_adult_height` 静默 clamp

**位置**：[growth_standards.py:54](backend/app/utils/growth_standards.py#L54)：
```python
predicted_height = min(max(predicted_height, 140), 220)
```
幼儿外推出 350cm 被夹成 220cm，70cm 身高被夹成 140cm，外部无任何提示。

**解决方法**：
```python
def predict_adult_height(current_height_cm, bone_age_years, gender):
    if not current_height_cm or current_height_cm <= 0: return None
    pct = get_percent_adult_height(bone_age_years, gender)
    raw = current_height_cm / pct
    if raw < 140 or raw > 220:
        return {"value": None, "status": "out_of_domain", "raw": round(raw, 1)}
    return {"value": round(raw, 1), "status": "ok"}
```
或保持返回浮点，但同时返回 `adult_height_status`。

---

### Bug O. `JointGrader.load_all` 模型缺失时静默降级

**位置**：[main.py:202-204](backend/app/main.py#L202)。没加载的关节模型会在 `predict_detected_joints` 被标 `status="model_missing"`，然后 `semantic_align_missing_joint_grades` 用邻居 × 0.95 填。响应顶层没有"本次有 N 个关节无对应模型"的醒目标志。

**解决方法**：在 `JointGrader` 暴露 `missing_models: set[str]`，端点响应加一个 `joint_model_health`：
```python
return {
    ...,
    "joint_model_health": {
        "loaded": sorted(joint_grader.models.keys()),
        "missing": sorted(joint_grader.missing_models),
        "imputed_joint_count": sum(1 for v in joint_semantic_13.values() if v.get("imputed")),
    },
}
```

---

### Bug P. 密码强度校验覆盖不全

**位置**：
- `_ensure_builtin_accounts` [main.py:1633](backend/app/main.py#L1633) 直接写弱密码，**绕过** `_validate_password_strength`；
- `PATCH /auth/users/{id}/role` 不涉及改密；
- `POST /auth/users` [2381](backend/app/main.py#L2381) 则要求强密码。

**解决方法**：把 `_validate_password_strength` 放到一个共用 helper 且**所有写入点**都调用；删掉 `_ensure_builtin_accounts` 的硬编码弱密码（见 Bug D）。

---

### Bug Q. 遗留 `predictions` 跨库迁移非事务

**位置**：[main.py:1765-1813](backend/app/main.py#L1765)：读 auth.db 的 predictions → 写 predictions.db，两步分别在不同 `with` 里；中途失败 + 下次因 `pred_count > 0` 不再迁移 = 老数据永远丢失。

**解决方法**：用 `ATTACH DATABASE` + 单事务：
```python
with connect(settings.prediction_db_path) as pc:
    pc.execute("BEGIN")
    try:
        pc.execute(f"ATTACH DATABASE ? AS legacy", (settings.auth_db_path,))
        pc.execute("""
            INSERT OR IGNORE INTO predictions
            SELECT * FROM legacy.predictions
        """)
        pc.execute("DETACH DATABASE legacy")
        pc.execute("COMMIT")
    except Exception:
        pc.execute("ROLLBACK"); raise
```

---

### Bug R. `/bone-age-points` GET 不校验 `user_id` 是否为 `user` 角色

**位置**：[main.py:3191-3213](backend/app/main.py#L3191)。医生传入任意 `user_id` 直接查；其它端点（如 `/predict` 的 `target_user_id`）通过 `_fetch_patient_user_or_raise` 做了"必须是 user 角色"校验。

**解决方法**：统一走 `_fetch_patient_user_or_raise`，或显式允许医生查询任意角色但在响应中暴露目标 role（避免前端把 doctor 的 points 当成"患者 points"展示）。

---

### Bug S. `update_prediction` 允许写入 0 值

**位置**：`PredictionUpdateRequest` 字段全部 `ge=0.0`（[2547-2555](backend/app/main.py#L2547)）。写入 `predicted_age_years=0` 或 `bone_age_years=0` 会合法通过校验，并同步更新 `bone_age_points`，污染趋势拟合。

**解决方法**：`ge=0.05` + 上限校验，并在 `update_prediction` 里显式 reject 0：
```python
predicted_age_years: Optional[float] = Field(default=None, gt=0.0, le=30.0)
```

---

### Bug T. `SmallJointRecognizer.recognize_13` 非等比 resize 后按比例回填 bbox

**位置**：[main.py:527](backend/app/main.py#L527) `cv2.resize(img_bgr_orig, (self.imgsz, self.imgsz))` 非等比，再用 `scale_x = w/imgsz`、`scale_y = h/imgsz` 做线性回填（[586-594](backend/app/main.py#L586)）。对极端宽高比图像只是近似。

**解决方法**：使用 letterbox（保持比例 + 填充），并记录填充偏移用于回填：
```python
def letterbox(img, new_shape=1024, color=(114,114,114)):
    h, w = img.shape[:2]; r = min(new_shape/h, new_shape/w)
    nh, nw = int(round(h*r)), int(round(w*r))
    pad_w, pad_h = (new_shape - nw)//2, (new_shape - nh)//2
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    out = np.full((new_shape, new_shape, 3), color, dtype=img.dtype)
    out[pad_h:pad_h+nh, pad_w:pad_w+nw] = resized
    return out, r, pad_w, pad_h
# 回填：x_orig = (x - pad_w) / r
```

---

## 三、附：测试与持续改进建议

1. 锁住关键语义的单元测试：
   - `hand_side.resolve` 三个用例（radius>ulna、radius<ulna、缺失）
   - `calc_bone_age_from_score` 在 score=0 / 500 / 1000 的行为
   - `align_joint_semantics` 在 `MCP` → `MCPThird/MCPFifth` 映射的分裂逻辑
2. 一个端到端冒烟：上传一张小样本 → `/predict` → 校验 `joint_model_health`、`rus_bone_age_years` 非空。
3. 清理项目根与 `backend/` 目录下十余份 `*_FIX_*.md` 和 `_predict_try.py`、`debug_*.py`、`test_*.jpg`：建议移到 `docs/history/` 或删除，以免审查时被误当作生产代码。

---

**附录 — 审查文件引用索引**

- 入口与主路由：[backend/app/main.py](backend/app/main.py)
- 配置：[backend/app/config.py](backend/app/config.py)
- RUS 评分与公式：[backend/app/utils/rus_chn.py](backend/app/utils/rus_chn.py)
- 生长标准：[backend/app/utils/growth_standards.py](backend/app/utils/growth_standards.py)
- 异物检测辅助：[backend/app/utils/foreign_object_detection.py](backend/app/utils/foreign_object_detection.py)
- Grad-CAM：[backend/app/utils/gradcam.py](backend/app/utils/gradcam.py)
- 通知服务：[backend/app/utils/notification_service.py](backend/app/utils/notification_service.py)
- 骨折 ONNX：[backend/app/detector_of_bone/main.py](backend/app/detector_of_bone/main.py)（重复，建议删）
- DP V3 骨骼检测：[backend/dp_bone_detector_v3.py](backend/dp_bone_detector_v3.py)
- 服务入口：[backend/entry_point.py](backend/entry_point.py)
