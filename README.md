# Health Moments Study Web App

Flask web app for participant onboarding, baseline setup, Qualtrics survey links, and weekly completion tracking.

## English

### Features
- Participant login with `Name + Participant ID`
- Consent content shown on the login page
- First-time participants must complete the Baseline survey and select a dashboard start date before entering Dashboard
- Dashboard provides Morning and Moment Qualtrics survey links
- Dashboard shows weekly Morning completion and Moment response counts
- Qualtrics webhook updates survey completion data
- Baseline status refreshes automatically with polling and server-sent events

### Tech Stack
- Flask
- MySQL
- mysql-connector-python
- python-dotenv

### Project Structure
```text
app.py                    # app factory + blueprint registration
models.py                 # lightweight data models
blueprints/
  auth.py                 # login, baseline setup, baseline status routes
  dashboard.py            # dashboard page and dashboard status route
  webhook.py              # Qualtrics webhook route
services/
  db_service.py           # MySQL connection, schema bootstrap, SQL access
  time_service.py         # timestamp and timezone helpers
  session_service.py      # baseline session and status payload helpers
  dashboard_service.py    # dashboard week and completion logic
  webhook_service.py      # webhook persistence logic
templates/
static/
tests/
```

### Important Routes
- `GET/POST /` - Login
- `GET/POST /baseline-info` - Baseline setup page
- `POST /api/set-calendar-start-date` - Save participant-selected dashboard start date
- `GET /baseline-status` - Baseline setup status JSON
- `GET /baseline-status-stream` - Baseline setup status SSE stream
- `GET /dashboard` - Participant dashboard
- `GET /dashboard-status` - Dashboard status JSON
- `POST /webhook/qualtrics` - Qualtrics webhook endpoint

### Dashboard Week Counting
- Week counting is anchored to the participant-selected `calendar_start_date`.
- Week 1 starts on the selected start date.
- If the selected start date is in the future, Dashboard still shows Week 1.
- Week 2 starts after 7 elapsed days.
- Example: if `calendar_start_date` is `2026-06-03`, then:
  - `2026-06-03` through `2026-06-09` are Week 1
  - `2026-06-10` starts Week 2

### Dashboard Completion Logic
- Morning survey completion is read from `daily_responses`.
- Moment survey counts are read from `event_responses`.
- Records are grouped by Central Time day boundaries.
- Morning shows completed when at least one `daily_responses` row exists for that day.
- Moment shows the number of `event_responses` rows for that day.
- These rows are written by the Qualtrics webhook, not by clicking the survey links.

### Webhook Payload
`POST /webhook/qualtrics` expects JSON with:
- `user_id`
- `response_id`
- `survey_type`: `baseline`, `daily`, or `event`
- `status`

Optional timestamp fields:
- `timestamp`
- `recorded_at`
- `recordedDate`

`screening` is accepted for legacy data, but it is not required for the current flow.

### Database Setup
Create the database before starting the app:

```sql
CREATE DATABASE Health_Moment CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

The app creates missing tables on startup. It also adds missing compatibility columns, including:
- `users.start_date_central_time`
- `users.screening_completed`
- `users.baseline_completed`
- `users.screening_id`
- `users.baseline_id`
- `users.calendar_start_date`
- `daily_responses.central_time`
- `event_responses.central_time`

For production, check schema before deploy:

```sql
SHOW COLUMNS FROM users LIKE 'calendar_start_date';
```

If the column is missing and the app DB user does not have `ALTER` permission, run:

```sql
ALTER TABLE users
ADD COLUMN calendar_start_date BIGINT DEFAULT NULL;
```

### Environment Variables
Create `.env` in the project root:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=Health_Moment
DB_AUTH_PLUGIN=mysql_native_password
DB_CHARSET=utf8mb4
```

You can copy `.env.example` and adjust it. The app reads `.env`; `.env.example` is only a template.

### Install and Run
```bash
pip install -r requirements.txt
python app.py
```

Default local URL:

```text
http://127.0.0.1:5001
```

### Tests
Run the dashboard week calculation tests:

```bash
python3 -m unittest discover -s tests
```

Run Python syntax checks:

```bash
python3 -m compileall app.py blueprints services models.py tests
```

### Deployment Notes
- Back up the production database before deploy.
- Confirm `users.calendar_start_date` exists or manually add it.
- If the app is deployed behind a reverse proxy or under a URL prefix, use Flask-generated URLs in templates. Do not hardcode root-relative API paths.
- Baseline status SSE is process-local. Multi-worker deployments need shared pub/sub if real-time updates must work across workers.
- Morning and Moment completion depends on Qualtrics webhook delivery. If Dashboard does not update, check webhook logs and the `daily_responses` / `event_responses` tables first.

---

## 中文

### 功能简介
- 使用 `姓名 + Participant ID` 登录
- 登录页展示 Consent 内容
- 首次用户需要完成 Baseline 问卷并选择 Dashboard 起始日期，之后才能进入 Dashboard
- Dashboard 提供 Morning 和 Moment 的 Qualtrics 问卷链接
- Dashboard 展示每周 Morning 完成情况和 Moment 提交次数
- Qualtrics webhook 写入问卷完成数据
- Baseline 页面通过轮询和 SSE 自动刷新状态

### 技术栈
- Flask
- MySQL
- mysql-connector-python
- python-dotenv

### 项目结构
```text
app.py                    # 应用工厂 + 蓝图注册
models.py                 # 轻量数据模型
blueprints/
  auth.py                 # 登录、baseline setup、baseline 状态路由
  dashboard.py            # dashboard 页面与 dashboard 状态路由
  webhook.py              # Qualtrics webhook 路由
services/
  db_service.py           # MySQL 连接、schema 初始化、SQL 访问
  time_service.py         # 时间戳和时区辅助方法
  session_service.py      # baseline session 和状态 payload 辅助方法
  dashboard_service.py    # dashboard week 和完成状态逻辑
  webhook_service.py      # webhook 写入逻辑
templates/
static/
tests/
```

### 重要路由
- `GET/POST /` - 登录
- `GET/POST /baseline-info` - Baseline setup 页面
- `POST /api/set-calendar-start-date` - 保存用户选择的 Dashboard 起始日期
- `GET /baseline-status` - Baseline setup 状态 JSON
- `GET /baseline-status-stream` - Baseline setup 状态 SSE stream
- `GET /dashboard` - 用户 Dashboard
- `GET /dashboard-status` - Dashboard 状态 JSON
- `POST /webhook/qualtrics` - Qualtrics webhook endpoint

### Dashboard Week 计数规则
- Week 计数以用户选择的 `calendar_start_date` 为起点。
- Week 1 从用户选择的起始日期开始。
- 如果起始日期还在未来，Dashboard 仍显示 Week 1。
- 满 7 个 elapsed days 后进入 Week 2。
- 例子：如果 `calendar_start_date` 是 `2026-06-03`：
  - `2026-06-03` 到 `2026-06-09` 是 Week 1
  - `2026-06-10` 开始是 Week 2

### Dashboard 完成状态逻辑
- Morning survey 完成状态来自 `daily_responses` 表。
- Moment survey 次数来自 `event_responses` 表。
- 记录按 Central Time 的每日边界分组。
- 某天至少有 1 条 `daily_responses` 记录时，Morning 显示完成。
- 某天的 Moment 显示该日 `event_responses` 记录数量。
- 这些记录由 Qualtrics webhook 写入，不是用户点击问卷链接时写入。

### Webhook 数据格式
`POST /webhook/qualtrics` 需要 JSON 字段：
- `user_id`
- `response_id`
- `survey_type`：`baseline`、`daily` 或 `event`
- `status`

可选时间字段：
- `timestamp`
- `recorded_at`
- `recordedDate`

`screening` 会被兼容接受，但当前流程不需要。

### 数据库设置
启动应用前先创建数据库：

```sql
CREATE DATABASE Health_Moment CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

应用启动时会自动创建缺失的表，也会补齐兼容字段，包括：
- `users.start_date_central_time`
- `users.screening_completed`
- `users.baseline_completed`
- `users.screening_id`
- `users.baseline_id`
- `users.calendar_start_date`
- `daily_responses.central_time`
- `event_responses.central_time`

生产部署前检查 schema：

```sql
SHOW COLUMNS FROM users LIKE 'calendar_start_date';
```

如果字段不存在，且线上应用数据库账号没有 `ALTER` 权限，手动执行：

```sql
ALTER TABLE users
ADD COLUMN calendar_start_date BIGINT DEFAULT NULL;
```

### 环境变量
在项目根目录创建 `.env`：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=Health_Moment
DB_AUTH_PLUGIN=mysql_native_password
DB_CHARSET=utf8mb4
```

可以复制 `.env.example` 后修改。程序读取 `.env`，`.env.example` 只是模板。

### 安装和启动
```bash
pip install -r requirements.txt
python app.py
```

默认本地访问地址：

```text
http://127.0.0.1:5001
```

### 测试
运行 Dashboard week 计算测试：

```bash
python3 -m unittest discover -s tests
```

运行 Python 语法检查：

```bash
python3 -m compileall app.py blueprints services models.py tests
```

### 部署注意事项
- 部署前备份生产数据库。
- 确认 `users.calendar_start_date` 存在，或提前手动添加。
- 如果应用在反向代理后面，或部署在 URL prefix 下，模板里应使用 Flask 生成的 URL，不要硬编码根路径 API。
- Baseline 状态 SSE 是进程内的。多 worker 部署如果需要跨 worker 实时更新，需要共享 pub/sub。
- Morning 和 Moment 完成状态依赖 Qualtrics webhook 投递。Dashboard 不更新时，先检查 webhook 日志和 `daily_responses` / `event_responses` 表。
