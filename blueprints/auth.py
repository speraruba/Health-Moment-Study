from queue import Queue

from flask import Blueprint, Response, jsonify, redirect, render_template, request, session, url_for

from extensions import db
from models import User
from services.session_service import build_baseline_status_payload, establish_existing_user_session
from services.sse_service import baseline_status_subscribers, stream_sse


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
            user = User.query.filter_by(user_id=user_id).first()

            if user:
                if user.username == "Unknown_User":
                    user.username = username_input_lower
                    db.session.commit()
                    establish_existing_user_session(user)
                    return redirect(url_for('dashboard.dashboard'))

                if user.username.lower() != username_input_lower:
                    error = "The name does not match this ID. Please try again."
                else:
                    establish_existing_user_session(user)
                    return redirect(url_for('dashboard.dashboard'))
            else:
                new_user = User(user_id=user_id, username=username_input_lower)
                db.session.add(new_user)
                db.session.commit()

                session['user_id'] = user_id
                session['pending_consent_user_id'] = user_id
                session.pop('pending_baseline_user_id', None)
                return redirect(url_for('auth.consent'))

    return render_template('login.html', error=error)


@bp.route('/api/user-exists')
def user_exists():
    user_id = request.args.get('user_id', '').strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    exists = User.query.filter_by(user_id=user_id).first() is not None
    return jsonify({"exists": exists}), 200


@bp.route('/consent', methods=['GET', 'POST'])
def consent():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    current_uid = session['user_id']
    pending_uid = session.get('pending_consent_user_id')
    pending_baseline_uid = session.get('pending_baseline_user_id')

    if pending_uid != current_uid:
        if pending_baseline_uid == current_uid:
            return redirect(url_for('auth.baseline_info'))
        return redirect(url_for('dashboard.dashboard'))

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
            return redirect(url_for('auth.baseline_info'))

    return render_template('consent.html', error=error)


@bp.route('/baseline-info', methods=['GET', 'POST'])
def baseline_info():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    current_uid = session['user_id']
    pending_uid = session.get('pending_baseline_user_id')
    user = User.query.filter_by(user_id=current_uid).first()

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    if pending_uid != current_uid:
        if session.get('pending_consent_user_id') == current_uid:
            return redirect(url_for('auth.consent'))
        return redirect(url_for('dashboard.dashboard'))

    screening_done = bool(user.screening_completed)
    baseline_done = bool(user.baseline_completed)
    all_done = screening_done and baseline_done

    error = None
    if request.method == 'POST':
        db.session.refresh(user)
        if user.screening_completed and user.baseline_completed:
            session.pop('pending_baseline_user_id', None)
            return redirect(url_for('dashboard.dashboard'))
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


@bp.route('/baseline-status')
def baseline_status():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    current_uid = session['user_id']
    user = User.query.filter_by(user_id=current_uid).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(build_baseline_status_payload(user)), 200


@bp.route('/baseline-status-stream')
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

