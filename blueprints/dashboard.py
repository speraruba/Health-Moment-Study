from queue import Queue

from flask import Blueprint, Response, jsonify, redirect, render_template, session, url_for

from services.db_service import get_user_by_id
from services.dashboard_service import build_dashboard_context
from services.sse_service import dashboard_subscribers, stream_sse


bp = Blueprint('dashboard', __name__)


@bp.route('/dashboard-stream')
def dashboard_stream():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_uid = session['user_id']
    user = get_user_by_id(current_uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    subscriber = Queue()
    dashboard_subscribers[current_uid].append(subscriber)
    return Response(
        stream_sse(subscriber, dashboard_subscribers, current_uid),
        mimetype='text/event-stream'
    )


@bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    current_uid = session['user_id']
    if session.get('pending_consent_user_id') == current_uid:
        return redirect(url_for('auth.consent'))
    if session.get('pending_baseline_user_id') == current_uid:
        return redirect(url_for('auth.baseline_info'))

    user = get_user_by_id(current_uid)
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    dashboard_context = build_dashboard_context(user, current_uid)
    return render_template(
        'dashboard.html',
        user_id=current_uid,
        username=user.username,
        **dashboard_context
    )
