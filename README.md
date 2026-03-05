# Health Moments Study Web App

## English

### What this app does
- Participant login with `Name + Participant ID`
- First-time users complete Consent, then Baseline Info forms, then enter Dashboard
- Dashboard provides Daily/Event Qualtrics links and weekly history
- Qualtrics webhook updates survey completion data in real time

### Install dependencies
1. (Optional) Create and activate a virtual environment.
2. Install packages:

```bash
pip install -r requirements.txt
```

### Start the app
1. Make sure MySQL is running.
2. Ensure database `Health_Moment` exists and the connection string in `app.py` is correct.
3. Run:

```bash
python app.py
```

The app starts at `http://127.0.0.1:5000` by default.

---

## 中文

### 功能简介
- 使用 `姓名 + Participant ID` 登录
- 首次登录用户先完成 Consent，再完成 Baseline 信息页，之后进入 Dashboard
- Dashboard 提供 Daily/Event 的 Qualtrics 链接和每周历史记录
- 通过 Qualtrics webhook 实时更新问卷完成状态

### 安装依赖
1. （可选）创建并激活虚拟环境。
2. 安装依赖：

```bash
pip install -r requirements.txt
```

### 启动项目
1. 确保 MySQL 已启动。
2. 确保已创建数据库 `Health_Moment`，并检查 `app.py` 中的数据库连接配置。
3. 启动：

```bash
python app.py
```

默认访问地址：`http://127.0.0.1:5000`。
