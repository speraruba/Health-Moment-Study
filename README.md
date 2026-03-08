# Health Moments Study Web App

## English

### What this app does
- Participant login with `Name + Participant ID`
- First-time users complete Consent, then Baseline Info forms, then enter Dashboard
- Dashboard provides Daily/Event Qualtrics links and weekly history
- Qualtrics webhook updates survey completion data in real time

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
  dashboard.py            # dashboard + dashboard stream routes
  webhook.py              # Qualtrics webhook route
services/
  db_service.py           # mysql.connector connection + SQL access
  time_service.py         # timestamp/timezone helpers
  session_service.py      # session/payload helpers
  sse_service.py          # SSE publish + stream helpers
  dashboard_service.py    # dashboard stats logic
  webhook_service.py      # webhook persistence logic
templates/
static/
```

### Install dependencies
1. (Optional) Create and activate a virtual environment.
2. Install packages:
```bash
pip install -r requirements.txt
```

### Start the app
1. Make sure MySQL is running.
2. Ensure database `Health_Moment` exists.
3. Set DB environment variables if needed: `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_AUTH_PLUGIN`, `DB_CHARSET`.
4. Run:
```bash
python app.py
```

Default URL: `http://127.0.0.1:5001`


---

## 中文

### 功能简介
- 使用 `姓名 + Participant ID` 登录
- 首次登录用户先完成 Consent，再完成 Baseline 信息页，之后进入 Dashboard
- Dashboard 提供 Daily/Event 的 Qualtrics 链接和每周历史记录
- 通过 Qualtrics webhook 实时更新问卷完成状态

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
  dashboard.py            # dashboard 与 dashboard SSE 路由
  webhook.py              # Qualtrics webhook 路由
services/
  db_service.py           # mysql.connector 连接与 SQL 访问
  time_service.py         # 时间戳/时区辅助方法
  session_service.py      # session/payload 辅助方法
  sse_service.py          # SSE 发布与流处理
  dashboard_service.py    # dashboard 统计逻辑
  webhook_service.py      # webhook 数据写入逻辑
templates/
static/
```

### 安装依赖
1. （可选）创建并激活虚拟环境。
2. 安装依赖：
```bash
pip install -r requirements.txt
```

### 启动项目
1. 确保 MySQL 已启动。
2. 确保数据库 `Health_Moment` 已创建。
3. 按需设置数据库环境变量：`DB_USER`、`DB_PASSWORD`、`DB_HOST`、`DB_PORT`、`DB_NAME`、`DB_AUTH_PLUGIN`、`DB_CHARSET`。
4. 运行：
```bash
python app.py
```

默认访问地址：`http://127.0.0.1:5001`
