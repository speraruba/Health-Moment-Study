from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone, time
from sqlalchemy import inspect, text
from collections import defaultdict
from queue import Queue, Empty
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost:3306/Health_Moment'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
baseline_status_subscribers = defaultdict(list)
dashboard_subscribers = defaultdict(list)


def current_utc_timestamp():
    return int(datetime.now(timezone.utc).timestamp())


def normalize_unix_timestamp(value):
    """Normalize webhook time input to unix timestamp (seconds)."""
    if value is None:
        return current_utc_timestamp()

    if isinstance(value, (int, float)):
        ts = float(value)
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return current_utc_timestamp()

        try:
            ts = float(raw)
        except ValueError:
            iso_raw = raw.replace('Z', '+00:00')
            try:
                dt = datetime.fromisoformat(iso_raw)
            except ValueError:
                return current_utc_timestamp()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.astimezone(timezone.utc).timestamp())
    else:
        return current_utc_timestamp()

    # Qualtrics side sometimes sends milliseconds.
    if ts > 1_000_000_000_000:
        ts = ts / 1000
    return int(ts)


# ================= 数据库模型 =================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    # 用户注册时间（UTC 秒级时间戳）
    start_date = db.Column(db.BigInteger, nullable=False, default=current_utc_timestamp)
    screening_completed = db.Column(db.Boolean, nullable=False, default=False)
    baseline_completed = db.Column(db.Boolean, nullable=False, default=False)

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
    timestamp = db.Column(db.BigInteger, nullable=False, default=current_utc_timestamp)


# 拆分表 2：活动打卡表
class EventResponse(db.Model):
    __tablename__ = 'event_responses'
    id = db.Column(db.Integer, primary_key=True)  # 自增主键，允许单用户多条记录

    # user_id 作为外键，关联到 users 表的 user_id
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'), nullable=False)

    response_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.BigInteger, nullable=False, default=current_utc_timestamp)


# 创建表
def ensure_users_completion_columns():
    inspector = inspect(db.engine)
    existing_columns = {col['name'] for col in inspector.get_columns('users')}

    alter_statements = []
    if 'screening_completed' not in existing_columns:
        alter_statements.append(
            "ALTER TABLE users ADD COLUMN screening_completed BOOLEAN NOT NULL DEFAULT 0"
        )
    if 'baseline_completed' not in existing_columns:
        alter_statements.append(
            "ALTER TABLE users ADD COLUMN baseline_completed BOOLEAN NOT NULL DEFAULT 0"
        )

    for stmt in alter_statements:
        db.session.execute(text(stmt))
    if alter_statements:
        db.session.commit()


def build_baseline_status_payload(user):
    screening_completed = bool(user.screening_completed)
    baseline_completed = bool(user.baseline_completed)
    return {
        "screening_completed": screening_completed,
        "baseline_completed": baseline_completed,
        "all_completed": screening_completed and baseline_completed,
    }


def sync_pending_baseline_session(user):
    if user.screening_completed and user.baseline_completed:
        session.pop('pending_baseline_user_id', None)
    else:
        session['pending_baseline_user_id'] = user.user_id


def establish_existing_user_session(user):
    session['user_id'] = user.user_id
    session.pop('pending_consent_user_id', None)
    sync_pending_baseline_session(user)


def get_or_create_webhook_user(user_id):
    user = User.query.filter_by(user_id=user_id).first()
    if user:
        return user
    user = User(user_id=user_id, username="Unknown_User")
    db.session.add(user)
    db.session.commit()
    return user


def stream_sse(subscriber, subscriber_map, user_id, initial_payload=None):
    try:
        if initial_payload is not None:
            yield f"data: {json.dumps(initial_payload)}\n\n"

        while True:
            try:
                payload = subscriber.get(timeout=30)
                yield f"data: {json.dumps(payload)}\n\n"
            except Empty:
                yield ": ping\n\n"
    finally:
        listeners = subscriber_map.get(user_id, [])
        if subscriber in listeners:
            listeners.remove(subscriber)
        if not listeners:
            subscriber_map.pop(user_id, None)


def record_response_if_new(model, user_id, response_id, status, response_timestamp):
    existing_response = model.query.filter_by(response_id=response_id).first()
    if existing_response:
        return False

    db.session.add(
        model(
            user_id=user_id,
            response_id=response_id,
            status=status,
            timestamp=response_timestamp
        )
    )
    db.session.commit()
    return True


def count_completed_responses(model, user_id, start_ts, end_ts):
    return model.query.filter(
        model.user_id == user_id,
        model.timestamp >= start_ts,
        model.timestamp < end_ts,
        model.status == 'completed'
    ).count()


def publish_baseline_status(user_id):
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return

    payload = build_baseline_status_payload(user)

    for subscriber in list(baseline_status_subscribers.get(user_id, [])):
        subscriber.put(payload)


def publish_dashboard_update(user_id):
    payload = {
        "updated": True,
        "timestamp": current_utc_timestamp()
    }
    for subscriber in list(dashboard_subscribers.get(user_id, [])):
        subscriber.put(payload)


def resolve_dashboard_timezone():
    """Resolve user's dashboard timezone from query param/session; fallback to UTC."""
    tz_name = request.args.get('tz', '').strip()
    if tz_name:
        try:
            tz = ZoneInfo(tz_name)
            session['dashboard_timezone'] = tz_name
            return tz
        except ZoneInfoNotFoundError:
            pass

    saved_tz_name = session.get('dashboard_timezone', '')
    if saved_tz_name:
        try:
            return ZoneInfo(saved_tz_name)
        except ZoneInfoNotFoundError:
            session.pop('dashboard_timezone', None)

    return timezone.utc


def local_day_bounds_to_utc_timestamps(local_date, user_tz):
    """Convert a local calendar day to UTC timestamp bounds for DB query."""
    local_start = datetime.combine(local_date, time.min, tzinfo=user_tz)
    local_end = local_start + timedelta(days=1)
    utc_start_ts = int(local_start.astimezone(timezone.utc).timestamp())
    utc_end_ts = int(local_end.astimezone(timezone.utc).timestamp())
    return utc_start_ts, utc_end_ts


with app.app_context():
    db.create_all()
    ensure_users_completion_columns()


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
                    establish_existing_user_session(user)
                    return redirect(url_for('dashboard'))

                # 正常校验：校验该输入的 username(小写) 和数据库中的 username(小写) 是否一致
                elif user.username.lower() != username_input_lower:
                    # 如果不一致，提示用户重新输入
                    error = "The name does not match this ID. Please try again."
                else:
                    # 如果一致，通过校验，允许登录
                    establish_existing_user_session(user)
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
                session.pop('pending_baseline_user_id', None)
                return redirect(url_for('consent'))

    return render_template('login.html', error=error)


@app.route('/api/user-exists')
def user_exists():
    user_id = request.args.get('user_id', '').strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    exists = User.query.filter_by(user_id=user_id).first() is not None
    return jsonify({"exists": exists}), 200


@app.route('/consent', methods=['GET', 'POST'])
def consent():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_uid = session['user_id']
    pending_uid = session.get('pending_consent_user_id')
    pending_baseline_uid = session.get('pending_baseline_user_id')

    if pending_uid != current_uid:
        if pending_baseline_uid == current_uid:
            return redirect(url_for('baseline_info'))
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
            session['pending_baseline_user_id'] = current_uid
            return redirect(url_for('baseline_info'))

    return render_template('consent.html', error=error)


@app.route('/baseline-info', methods=['GET', 'POST'])
def baseline_info():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_uid = session['user_id']
    pending_uid = session.get('pending_baseline_user_id')
    user = User.query.filter_by(user_id=current_uid).first()

    if not user:
        session.clear()
        return redirect(url_for('login'))

    if pending_uid != current_uid:
        if session.get('pending_consent_user_id') == current_uid:
            return redirect(url_for('consent'))
        return redirect(url_for('dashboard'))

    screening_done = bool(user.screening_completed)
    baseline_done = bool(user.baseline_completed)
    all_done = screening_done and baseline_done

    error = None
    if request.method == 'POST':
        db.session.refresh(user)
        if user.screening_completed and user.baseline_completed:
            session.pop('pending_baseline_user_id', None)
            return redirect(url_for('dashboard'))
        error = "Both screening and baseline forms must be completed before continuing."
        screening_done = bool(user.screening_completed)
        baseline_done = bool(user.baseline_completed)
        all_done = screening_done and baseline_done

    return render_template(
        'baseline_info.html',
        user_id=current_uid,
        screening_done=screening_done,
        baseline_done=baseline_done,
        all_done=all_done,
        error=error
    )


@app.route('/baseline-status')
def baseline_status():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_uid = session['user_id']
    user = User.query.filter_by(user_id=current_uid).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(build_baseline_status_payload(user)), 200


@app.route('/baseline-status-stream')
def baseline_status_stream():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_uid = session['user_id']
    user = User.query.filter_by(user_id=current_uid).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    subscriber = Queue()
    baseline_status_subscribers[current_uid].append(subscriber)

    return Response(
        stream_sse(
            subscriber,
            baseline_status_subscribers,
            current_uid,
            initial_payload=build_baseline_status_payload(user)
        ),
        mimetype='text/event-stream'
    )


@app.route('/dashboard-stream')
def dashboard_stream():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_uid = session['user_id']
    user = User.query.filter_by(user_id=current_uid).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    subscriber = Queue()
    dashboard_subscribers[current_uid].append(subscriber)

    return Response(
        stream_sse(subscriber, dashboard_subscribers, current_uid),
        mimetype='text/event-stream'
    )


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_uid = session['user_id']
    if session.get('pending_consent_user_id') == current_uid:
        return redirect(url_for('consent'))
    if session.get('pending_baseline_user_id') == current_uid:
        return redirect(url_for('baseline_info'))

    user = User.query.filter_by(user_id=current_uid).first()

    if not user:
        session.clear()
        return redirect(url_for('login'))

    user_tz = resolve_dashboard_timezone()
    local_today = datetime.now(timezone.utc).astimezone(user_tz).date()
    start_local_date = datetime.fromtimestamp(user.start_date, timezone.utc).astimezone(user_tz).date()
    days_participated = max(0, (local_today - start_local_date).days)
    weeks_participated = (days_participated // 7) + 1

    start_of_week = local_today - timedelta(days=local_today.weekday())

    daily_stats = []
    event_stats = []

    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        day_start_ts, day_end_ts = local_day_bounds_to_utc_timestamps(current_day, user_tz)

        daily_count = count_completed_responses(DailyResponse, current_uid, day_start_ts, day_end_ts)
        event_count = count_completed_responses(EventResponse, current_uid, day_start_ts, day_end_ts)

        daily_stats.append(daily_count > 0)
        event_stats.append(str(event_count) if event_count > 0 else '')

    # 【新增逻辑】：单独检查“今天”是否已经完成了 daily 问卷
    today_start_ts, tomorrow_start_ts = local_day_bounds_to_utc_timestamps(local_today, user_tz)
    daily_completed_today = (
        count_completed_responses(DailyResponse, current_uid, today_start_ts, tomorrow_start_ts) > 0
    )

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
    response_timestamp = normalize_unix_timestamp(
        data.get('timestamp') or data.get('recorded_at') or data.get('recordedDate')
    )
    survey_type = str(data.get('survey_type', '')).strip().lower()
    status = str(data.get('status', '')).strip().lower()

    if not all([user_id, response_id, survey_type, status]):
        return jsonify({"error": "Missing required fields"}), 400

    # 检查用户是否存在（满足外键约束）
    user = get_or_create_webhook_user(user_id)

    # 根据 survey_type 分别写入不同的表
    if survey_type == 'screening':
        if status == 'completed' and not user.screening_completed:
            user.screening_completed = True
            db.session.commit()
            publish_baseline_status(user_id)
        return jsonify({"message": "Screening status recorded"}), 200

    elif survey_type == 'baseline':
        if status == 'completed' and not user.baseline_completed:
            user.baseline_completed = True
            db.session.commit()
            publish_baseline_status(user_id)
        return jsonify({"message": "Baseline status recorded"}), 200

    elif survey_type in {'daily', 'event'}:
        response_model = DailyResponse if survey_type == 'daily' else EventResponse
        was_inserted = record_response_if_new(
            response_model,
            user_id=user_id,
            response_id=response_id,
            status=status,
            response_timestamp=response_timestamp
        )
        if was_inserted:
            publish_dashboard_update(user_id)
    else:
        return jsonify({"error": "Invalid survey_type"}), 400

    return jsonify({"message": "Data recorded successfully"}), 200


if __name__ == '__main__':
    #app.run(debug=True, port=5000)
    app.run(port=5001, debug=True)
