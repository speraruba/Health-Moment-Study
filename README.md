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

### Deploy with Passenger
This repo includes:
- `wsgi.py`: Primary WSGI app entry (exports `application`)
- `wagi.py`: Compatibility alias for existing host configs

Typical steps:
1. Upload project files to the server.
2. Create/activate virtual environment and install dependencies:
```bash
pip install -r requirements.txt
```
3. Configure Passenger app root to this project folder.
4. Set startup file to `wsgi.py` (or keep `wagi.py` if your host already uses it).
5. Update database connection in `app.py` for production.
6. Restart Passenger app.

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

### 使用 Passenger 部署
仓库已包含：
- `wsgi.py`：主 WSGI 入口（导出 `application`）
- `wagi.py`：兼容旧配置的别名入口

常见部署步骤：
1. 将项目文件上传到服务器。
2. 创建/激活虚拟环境并安装依赖：
```bash
pip install -r requirements.txt
```
3. 在 Passenger 中将应用根目录设置为本项目目录。
4. 启动文件设置为 `wsgi.py`（若托管已绑定 `wagi.py` 也可继续使用）。
5. 按生产环境修改 `app.py` 中数据库连接配置。
6. 重启 Passenger 应用。
