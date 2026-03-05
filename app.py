from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost:3306/Health_Moment'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ================= 数据库模型 =================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, default=datetime.utcnow().date)

    # 定义关联关系：方便查询，如果用户被删除，相关的打卡记录也会级联删除
    daily_responses = db.relationship('DailyResponse', backref='user', lazy=True, cascade="all, delete-orphan")
    event_responses = db.relationship('EventResponse', backref='user', lazy=True, cascade="all, delete-orphan")


# 拆分表 1：每日签到表
class DailyResponse(db.Model):
    __tablename__ = 'daily_responses'
    id = db.Column(db.Integer, primary_key=True)  # 自增主键，允许单用户多条记录

    # user_id 作为外键，关联到 users 表的 user_id
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'), nullable=False)

    response_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# 拆分表 2：活动打卡表
class EventResponse(db.Model):
    __tablename__ = 'event_responses'
    id = db.Column(db.Integer, primary_key=True)  # 自增主键，允许单用户多条记录

    # user_id 作为外键，关联到 users 表的 user_id
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'), nullable=False)

    response_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# 创建表
with app.app_context():
    db.create_all()


# ================= 路由逻辑 =================

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        username = request.form.get('username', '').strip()

        if not user_id or not username:
            error = "Name and Participant ID are required."
        else:
            # 1. 清理输入两端的空格，并将输入的 username 转换为小写用于后续对比
            username_input_lower = username.lower()

            # 2. 查询数据库中是否已经存在该 user_id
            user = User.query.filter_by(user_id=user_id).first()

            if user:
                # ==========================================
                # 逻辑分支 A：user_id 已经存在于数据库中
                # ==========================================

                # 兼容 Webhook：如果这个用户是 Webhook 提前创建的，数据库里名字是 "Unknown_User"
                # 此时我们允许他登录，并把他的真实名字（小写）正式更新到数据库中
                if user.username == "Unknown_User":
                    user.username = username_input_lower
                    db.session.commit()
                    session['user_id'] = user.user_id
                    return redirect(url_for('dashboard'))

                # 正常校验：校验该输入的 username(小写) 和数据库中的 username(小写) 是否一致
                elif user.username.lower() != username_input_lower:
                    # 如果不一致，提示用户重新输入
                    error = "The name does not match this ID. Please try again."
                else:
                    # 如果一致，通过校验，允许登录
                    session['user_id'] = user.user_id
                    session.pop('pending_consent_user_id', None)
                    return redirect(url_for('dashboard'))

            else:
                # ==========================================
                # 逻辑分支 B：user_id 不存在（新用户第一次登录）
                # ==========================================

                # 第一次储存用户名时，自动小写
                new_user = User(user_id=user_id, username=username_input_lower)
                db.session.add(new_user)
                db.session.commit()

                session['user_id'] = user_id
                session['pending_consent_user_id'] = user_id
                return redirect(url_for('consent'))

    return render_template('login.html', error=error)


@app.route('/consent', methods=['GET', 'POST'])
def consent():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_uid = session['user_id']
    pending_uid = session.get('pending_consent_user_id')

    if pending_uid != current_uid:
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        initial = request.form.get('initial', '').strip()
        agreed = request.form.get('agree') == 'on'

        if not initial:
            error = "Please enter your initial before continuing."
        elif not agreed:
            error = "Please confirm that you have read and agree before continuing."
        else:
            session.pop('pending_consent_user_id', None)
            return redirect(url_for('dashboard'))

    return render_template('consent.html', error=error)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_uid = session['user_id']
    if session.get('pending_consent_user_id') == current_uid:
        return redirect(url_for('consent'))

    user = User.query.filter_by(user_id=current_uid).first()

    if not user:
        session.clear()
        return redirect(url_for('login'))

    # 使用当天日期计算
    today = datetime.utcnow().date()
    days_participated = (today - user.start_date).days
    weeks_participated = (days_participated // 7) + 1

    start_of_week = today - timedelta(days=today.weekday())

    daily_stats = []
    event_stats = []

    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        next_day = current_day + timedelta(days=1)

        # 统计周一到周日每一天的数据
        daily_today = DailyResponse.query.filter(
            DailyResponse.user_id == current_uid,
            DailyResponse.timestamp >= current_day,
            DailyResponse.timestamp < next_day,
            DailyResponse.status == 'completed'
        ).all()

        event_today = EventResponse.query.filter(
            EventResponse.user_id == current_uid,
            EventResponse.timestamp >= current_day,
            EventResponse.timestamp < next_day,
            EventResponse.status == 'completed'
        ).all()

        has_daily = len(daily_today) > 0
        daily_stats.append(has_daily)

        event_count = len(event_today)
        event_stats.append(str(event_count) if event_count > 0 else '')

    # 【新增逻辑】：单独检查“今天”是否已经完成了 daily 问卷
    daily_completed_today = DailyResponse.query.filter(
        DailyResponse.user_id == current_uid,
        DailyResponse.timestamp >= today,
        DailyResponse.timestamp < today + timedelta(days=1),
        DailyResponse.status == 'completed'
    ).first() is not None

    return render_template('dashboard.html',
                           user_id=current_uid,
                           username=user.username,
                           weeks_participated=weeks_participated,
                           daily_stats=daily_stats,
                           event_stats=event_stats,
                           daily_completed_today=daily_completed_today)  # 将变量传给前端


# ... 后面的 Webhook 接口保持不变 ...

# ================= Webhook 接口 =================

@app.route('/webhook/qualtrics', methods=['POST'])
def qualtrics_webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    user_id = data.get('user_id')
    response_id = data.get('response_id')
    survey_type = data.get('survey_type')
    status = data.get('status')

    if not all([user_id, response_id, survey_type, status]):
        return jsonify({"error": "Missing required fields"}), 400

    # 检查用户是否存在（满足外键约束）
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        new_user = User(user_id=user_id, username="Unknown_User")
        db.session.add(new_user)
        db.session.commit()

    # 根据 survey_type 分别写入不同的表
    if survey_type == 'daily':
        existing_response = DailyResponse.query.filter_by(response_id=response_id).first()
        if not existing_response:
            new_response = DailyResponse(
                user_id=user_id,
                response_id=response_id,
                status=status
            )
            db.session.add(new_response)
            db.session.commit()

    elif survey_type == 'event':
        existing_response = EventResponse.query.filter_by(response_id=response_id).first()
        if not existing_response:
            new_response = EventResponse(
                user_id=user_id,
                response_id=response_id,
                status=status
            )
            db.session.add(new_response)
            db.session.commit()
    else:
        return jsonify({"error": "Invalid survey_type"}), 400

    return jsonify({"message": "Data recorded successfully"}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
