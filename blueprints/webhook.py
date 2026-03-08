from flask import Blueprint, jsonify, request

from extensions import db
from models import DailyResponse, EventResponse
from services.sse_service import publish_baseline_status, publish_dashboard_update
from services.time_service import normalize_unix_timestamp
from services.webhook_service import get_or_create_webhook_user, record_response_if_new


bp = Blueprint('webhook', __name__)


@bp.route('/webhook/qualtrics', methods=['POST'])
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

    user = get_or_create_webhook_user(user_id)

    if survey_type == 'screening':
        if status == 'completed' and not user.screening_completed:
            user.screening_completed = True
            db.session.commit()
            publish_baseline_status(user_id)
        return jsonify({"message": "Screening status recorded"}), 200

    if survey_type == 'baseline':
        if status == 'completed' and not user.baseline_completed:
            user.baseline_completed = True
            db.session.commit()
            publish_baseline_status(user_id)
        return jsonify({"message": "Baseline status recorded"}), 200

    if survey_type in {'daily', 'event'}:
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
        return jsonify({"message": "Data recorded successfully"}), 200

    return jsonify({"error": "Invalid survey_type"}), 400

