import json
import queue
import threading


_subscribers = {}
_lock = threading.Lock()


def subscribe_user(user_id):
    q = queue.Queue(maxsize=20)
    with _lock:
        _subscribers.setdefault(user_id, set()).add(q)
    return q


def unsubscribe_user(user_id, q):
    with _lock:
        queues = _subscribers.get(user_id)
        if not queues:
            return
        queues.discard(q)
        if not queues:
            _subscribers.pop(user_id, None)


def publish_user_event(user_id, payload):
    data = json.dumps(payload)
    with _lock:
        queues = list(_subscribers.get(user_id, set()))
    for q in queues:
        try:
            q.put_nowait(data)
        except queue.Full:
            continue
