import json
import queue
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)

from services.db_service import get_or_create_user, get_user_by_id, update_username, update_calendar_start_date
from services.realtime_service import subscribe_user, unsubscribe_user
from services.session_service import (
    build_baseline_status_payload,
    establish_existing_user_session,
    sync_pending_baseline_session,
)
from services.time_service import central_date_string, central_date_to_utc_timestamp, central_today


bp = Blueprint('auth', __name__)


@bp.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        username = request.form.get('username', '').strip()

        if not user_id or not username:
            error = "Name and Participant ID are required."
        else:
            username_input_lower = username.lower()
            user = get_user_by_id(user_id)

            if user:
                if user.username == "Unknown_User":
                    user = update_username(user_id, username_input_lower)
                    establish_existing_user_session(user)
                    return redirect(url_for('dashboard.dashboard'))

                if user.username.lower() != username_input_lower:
                    error = "The name does not match this ID. Please try again."
                else:
                    establish_existing_user_session(user)
                    return redirect(url_for('dashboard.dashboard'))
            else:
                user = get_or_create_user(user_id, username_input_lower)
                if user.username.lower() != username_input_lower:
                    error = "The name does not match this ID. Please try again."
                else:
                    session['user_id'] = user_id
                    session['pending_baseline_user_id'] = user_id
                    return redirect(url_for('auth.baseline_info'))

    return render_template('login.html', error=error)


@bp.route('/api/user-exists')
def user_exists():
    user_id = request.args.get('user_id', '').strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    exists = get_user_by_id(user_id) is not None
    return jsonify({"exists": exists}), 200


@bp.route('/api/set-calendar-start-date', methods=['POST'])
def set_calendar_start_date():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_uid = session['user_id']
    user = get_user_by_id(current_uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data or 'calendar_start_date' not in data:
        return jsonify({"error": "calendar_start_date is required"}), 400

    calendar_start_date_str = data.get('calendar_start_date', '').strip()

    try:
        date_obj = datetime.strptime(calendar_start_date_str, '%Y-%m-%d')
        calendar_start_date = central_date_to_utc_timestamp(date_obj.date())
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    today_ts = central_date_to_utc_timestamp(central_today())

    if calendar_start_date < today_ts:
        return jsonify({"error": "Calendar start date must not be in the past"}), 400

    updated_user = update_calendar_start_date(current_uid, calendar_start_date)
    return jsonify({
        "success": True,
        "message": "Calendar start date updated successfully",
        "calendar_start_date": updated_user.calendar_start_date
    }), 200


@bp.route('/baseline-info', methods=['GET', 'POST'])
def baseline_info():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    current_uid = session['user_id']
    pending_uid = session.get('pending_baseline_user_id')
    user = get_user_by_id(current_uid)

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    if pending_uid != current_uid:
        return redirect(url_for('dashboard.dashboard'))

    baseline_done = bool(user.baseline_completed)
    date_selected = bool(user.calendar_start_date)
    all_done = baseline_done and date_selected

    error = None
    if request.method == 'POST':
        user = get_user_by_id(current_uid)
        if user.baseline_completed and user.calendar_start_date:
            session.pop('pending_baseline_user_id', None)
            return redirect(url_for('dashboard.dashboard'))
        if not user.baseline_completed:
            error = "The baseline survey must be completed before continuing."
        elif not user.calendar_start_date:
            error = "Please select a calendar start date before continuing."
        baseline_done = bool(user.baseline_completed)
        date_selected = bool(user.calendar_start_date)
        all_done = baseline_done and date_selected

    return render_template(
        'baseline_info.html',
        user_id=current_uid,
        baseline_done=baseline_done,
        selected_calendar_date=central_date_string(user.calendar_start_date) if user.calendar_start_date else '',
        all_done=all_done,
        error=error
    )


@bp.route('/baseline-status')
def baseline_status():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_uid = session['user_id']
    user = get_user_by_id(current_uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    sync_pending_baseline_session(user)
    return jsonify(build_baseline_status_payload(user)), 200


@bp.route('/baseline-status-stream')
def baseline_status_stream():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_uid = session['user_id']
    user = get_user_by_id(current_uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    sync_pending_baseline_session(user)
    initial_payload = build_baseline_status_payload(user)

    def event_stream():
        q = subscribe_user(current_uid)
        last_payload = initial_payload
        try:
            yield f"event: status\ndata: {json.dumps(initial_payload)}\n\n"
            while True:
                try:
                    data = q.get(timeout=3)
                except queue.Empty:
                    refreshed_user = get_user_by_id(current_uid)
                    if not refreshed_user:
                        yield "event: status\ndata: " + json.dumps({"reload": True}) + "\n\n"
                        return

                    sync_pending_baseline_session(refreshed_user)
                    refreshed_payload = build_baseline_status_payload(refreshed_user)
                    if refreshed_payload != last_payload:
                        last_payload = refreshed_payload
                        yield f"event: status\ndata: {json.dumps(refreshed_payload)}\n\n"
                        continue

                    yield ": keep-alive\n\n"
                    continue
                last_payload = json.loads(data)
                yield f"event: status\ndata: {data}\n\n"
        finally:
            unsubscribe_user(current_uid, q)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return Response(stream_with_context(event_stream()), headers=headers, mimetype="text/event-stream")
