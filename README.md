# Health Moments Study Web App

## English

### What this app does
- Participant login with `Name + Participant ID`
- First-time users complete Consent, then Baseline survey, then enter Dashboard
- Dashboard provides Daily/Event Qualtrics links and weekly history
- Qualtrics webhook updates survey completion data, and the Baseline page uses SSE to refresh status automatically

### Dashboard week counting
- The "Week X" shown in the dashboard/history is based on 7-day blocks starting from the participant's `start_date` in the user's dashboard timezone.
- Week 1 is the first 7 days from the start date; Week 2 is the next 7 days, and so on.
- Example: if a participant joins on Friday, the following Friday will start Week 2.

### Tech stack
- Flask
- mysql-connector-python
- MySQL

### Current project structure
```text
app.py                    # app factory + blueprint registration
models.py                 # lightweight data models
blueprints/
  auth.py                 # login/consent/baseline/status routes
  dashboard.py            # dashboard + dashboard status routes
  webhook.py              # Qualtrics webhook route
services/
  db_service.py           # mysql.connector connection + SQL access
  time_service.py         # timestamp/timezone helpers
  session_service.py      # session/payload helpers
  dashboard_service.py    # dashboard stats logic
  webhook_service.py      # webhook persistence logic
templates/
static/
```

### Important routes
- App home: `/`
- Baseline status JSON: `/baseline-status`
- Dashboard status JSON: `/dashboard-status`
- Qualtrics webhook: `/webhook/qualtrics`

### Webhook payload
`POST /webhook/qualtrics` expects JSON with:
- `user_id`
- `response_id`
- `survey_type`: `baseline`, `daily`, or `event` (`screening` is accepted for legacy data but not required)
- `status`

Optional timestamp fields:
- `timestamp`
- `recorded_at`
- `recordedDate`

### Concurrency notes
- User creation is duplicate-safe for concurrent login/webhook requests on the same `user_id`
- Daily/event response writes are idempotent for duplicate Qualtrics deliveries with the same `response_id`
- Baseline status updates are pushed via in-memory SSE, so multi-worker deployments need a shared pub/sub layer if you want real-time updates across workers

### Install dependencies
1. (Optional) Create and activate a virtual environment.
2. Install packages:
```bash
pip install -r requirements.txt
```

### Environment variables
Create a `.env` file in the project root, for example:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=Health_Moment
DB_AUTH_PLUGIN=mysql_native_password
DB_CHARSET=utf8mb4
```

You can copy `.env.example` and adjust the values for your local or deployed database.
The app reads `.env`, not `.env.example`.
If a variable is missing from `.env`, the code falls back to these local defaults:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=Health_Moment
DB_AUTH_PLUGIN=mysql_native_password
DB_CHARSET=utf8mb4
```

### Start the app
1. Make sure MySQL is running.
2. Ensure database `Health_Moment` exists.
3. Create and update `.env` with your database credentials.
4. Run:
```bash
python app.py
```

Default URL: `http://127.0.0.1:5001`


---

## 中文

### 功能简介
- 使用 `姓名 + Participant ID` 登录
- 首次登录用户先完成 Consent，再完成 Baseline 问卷，之后进入 Dashboard
- Dashboard 提供 Daily/Event 的 Qualtrics 链接和每周历史记录
- 通过 Qualtrics webhook 更新问卷完成状态，Baseline 页面使用 SSE 自动刷新状态

### Dashboard Week 计数规则
- Dashboard/history 中显示的 “Week X” 按从 `start_date` 开始的连续 7 天为一周计数，且以用户的 dashboard 时区为准。
- 用户加入后的前 7 天为 Week 1，之后每满 7 天 Week +1。
- 例子：如果周五加入项目，那么到下一个周五开始 Week 2。

### 技术栈
- Flask
- mysql-connector-python
- MySQL

### 当前项目结构
```text
app.py                    # 应用工厂 + 蓝图注册
models.py                 # 轻量数据模型
blueprints/
  auth.py                 # 登录/同意书/baseline/状态相关路由
  dashboard.py            # dashboard 与 dashboard 状态路由
  webhook.py              # Qualtrics webhook 路由
services/
  db_service.py           # mysql.connector 连接与 SQL 访问
  time_service.py         # 时间戳/时区辅助方法
  session_service.py      # session/payload 辅助方法
  dashboard_service.py    # dashboard 统计逻辑
  webhook_service.py      # webhook 数据写入逻辑
templates/
static/
```

### 重要路由
- 首页：`/`
- Baseline 状态 JSON：`/baseline-status`
- Dashboard 状态 JSON：`/dashboard-status`
- Qualtrics webhook：`/webhook/qualtrics`

### Webhook 数据格式
`POST /webhook/qualtrics` 需要 JSON 字段：
- `user_id`
- `response_id`
- `survey_type`：`baseline`、`daily` 或 `event`（`screening` 为兼容历史数据，可选）
- `status`

可选时间字段：
- `timestamp`
- `recorded_at`
- `recordedDate`

### 并发说明
- 同一个 `user_id` 的并发登录或 webhook 建用户请求不会因重复创建直接报错
- 同一个 `response_id` 的重复 Qualtrics 投递会按幂等方式处理
- Baseline 状态使用进程内 SSE 推送，如果多 worker 部署且需要实时更新，需要接入共享的 pub/sub

### 安装依赖
1. （可选）创建并激活虚拟环境。
2. 安装依赖：
```bash
pip install -r requirements.txt
```

### 环境变量
在项目根目录创建 `.env`，例如：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=Health_Moment
DB_AUTH_PLUGIN=mysql_native_password
DB_CHARSET=utf8mb4
```

可以先复制 `.env.example`，再按本地或部署环境修改。
程序读取的是 `.env`，不是 `.env.example`。
如果 `.env` 中缺少某个变量，代码会回退到以下本地默认值：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=Health_Moment
DB_AUTH_PLUGIN=mysql_native_password
DB_CHARSET=utf8mb4
```

### 启动项目
1. 确保 MySQL 已启动。
2. 确保数据库 `Health_Moment` 已创建。
3. 创建并修改 `.env` 中的数据库连接参数。
4. 运行：
```bash
python app.py
```

默认访问地址：`http://127.0.0.1:5001`
