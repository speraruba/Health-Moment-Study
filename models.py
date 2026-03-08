from extensions import db
from services.time_service import current_utc_timestamp


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    # 用户注册时间（UTC 秒级时间戳）
    start_date = db.Column(db.BigInteger, nullable=False, default=current_utc_timestamp)
    screening_completed = db.Column(db.Boolean, nullable=False, default=False)
    baseline_completed = db.Column(db.Boolean, nullable=False, default=False)

    daily_responses = db.relationship('DailyResponse', backref='user', lazy=True, cascade="all, delete-orphan")
    event_responses = db.relationship('EventResponse', backref='user', lazy=True, cascade="all, delete-orphan")


class DailyResponse(db.Model):
    __tablename__ = 'daily_responses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'), nullable=False)
    response_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.BigInteger, nullable=False, default=current_utc_timestamp)


class EventResponse(db.Model):
    __tablename__ = 'event_responses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'), nullable=False)
    response_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.BigInteger, nullable=False, default=current_utc_timestamp)

