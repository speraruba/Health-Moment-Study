from flask import session


def build_baseline_status_payload(user):
    baseline_completed = bool(user.baseline_completed)
    return {
        "baseline_completed": baseline_completed,
        "all_completed": baseline_completed,
    }


def sync_pending_baseline_session(user):
    if user.baseline_completed:
        session.pop('pending_baseline_user_id', None)
    else:
        session['pending_baseline_user_id'] = user.user_id


def establish_existing_user_session(user):
    session['user_id'] = user.user_id
    session.pop('pending_consent_user_id', None)
    sync_pending_baseline_session(user)
