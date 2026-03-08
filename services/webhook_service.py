from extensions import db
from models import User


def get_or_create_webhook_user(user_id):
    user = User.query.filter_by(user_id=user_id).first()
    if user:
        return user

    user = User(user_id=user_id, username="Unknown_User")
    db.session.add(user)
    db.session.commit()
    return user


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

