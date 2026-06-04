from flask import session

from services.time_service import central_date_string


def build_baseline_status_payload(user):
    baseline_completed = bool(user.baseline_completed)
    date_selected = bool(user.calendar_start_date)
    return {
        "baseline_completed": baseline_completed,
        "calendar_start_date": central_date_string(user.calendar_start_date) if date_selected else None,
        "date_selected": date_selected,
        "all_completed": baseline_completed and date_selected,
    }


def sync_pending_baseline_session(user):
    if user.baseline_completed and user.calendar_start_date:
        session.pop('pending_baseline_user_id', None)
    else:
        session['pending_baseline_user_id'] = user.user_id


def establish_existing_user_session(user):
    session['user_id'] = user.user_id
    sync_pending_baseline_session(user)
