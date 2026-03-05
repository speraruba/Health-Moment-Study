# Health Moments Study Web App

## 1) Project Overview | 项目简介
English:
This is a Flask web app for the Health Moments Study. Participants log in with name and participant ID, complete consent (for first-time IDs), and then access daily/event survey links plus weekly history.

中文：
这是一个用于 Health Moments Study 的 Flask 应用。参与者使用姓名和参与者 ID 登录，首次新 ID 需要先完成知情同意，再进入 Dashboard 查看每日/事件问卷入口和历史记录。

## 2) Features | 功能
English:
- Login with `Name + Participant ID`
- New participant ID must complete Consent before entering Dashboard
- Daily survey button (disabled if already completed today)
- Event survey button
- Weekly history table
- Qualtrics webhook endpoint for recording survey responses

中文：
- 使用 `姓名 + Participant ID` 登录
- 新参与者 ID 必须先完成 Consent 页面才能进入 Dashboard
- 每日问卷按钮（当天完成后禁用）
- 事件问卷按钮
- 周历史记录表格
- 提供 Qualtrics Webhook 接口用于写入问卷结果

## 3) Tech Stack | 技术栈
English:
- Python
- Flask
- Flask-SQLAlchemy
- MySQL + PyMySQL

中文：
- Python
- Flask
- Flask-SQLAlchemy
- MySQL + PyMySQL

## 4) Setup | 环境准备
English:
1. Create and activate a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Ensure MySQL is running and create database `Health_Moment`.
4. Update database URL in `app.py` if needed.

中文：
1. 创建并激活虚拟环境。
2. 使用 `requirements.txt` 安装依赖。
3. 确保 MySQL 已启动，并创建数据库 `Health_Moment`。
4. 如有需要，修改 `app.py` 中数据库连接地址。

## 5) Install Dependencies | 安装依赖
```bash
pip install -r requirements.txt
```

## 6) Run the App | 启动应用
```bash
python app.py
```

English:
By default, the app runs at `http://127.0.0.1:5000`.

中文：
默认运行地址为 `http://127.0.0.1:5000`。

## 7) Webhook Endpoint | Webhook 接口
English:
- `POST /webhook/qualtrics`
- JSON fields: `user_id`, `response_id`, `survey_type` (`daily` or `event`), `status`

中文：
- `POST /webhook/qualtrics`
- JSON 字段：`user_id`、`response_id`、`survey_type`（`daily` 或 `event`）、`status`
