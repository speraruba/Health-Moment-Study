import json
from collections import defaultdict
from queue import Empty

from models import User
from services.session_service import build_baseline_status_payload
from services.time_service import current_utc_timestamp


baseline_status_subscribers = defaultdict(list)
dashboard_subscribers = defaultdict(list)


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

