from datetime import datetime, timedelta, timezone

from models import DailyResponse, EventResponse
from services.db_service import count_completed_responses as count_completed_rows
from services.time_service import resolve_dashboard_timezone, local_day_bounds_to_utc_timestamps


def count_completed_records(model, user_id, start_ts, end_ts):
    return count_completed_rows(model.table_name, user_id, start_ts, end_ts)


def build_dashboard_context(user, user_id):
    user_tz = resolve_dashboard_timezone()
    local_today = datetime.now(timezone.utc).astimezone(user_tz).date()
    start_local_date = datetime.fromtimestamp(user.start_date, timezone.utc).astimezone(user_tz).date()
    # Count weeks by natural (Mon-Sun) calendar weeks in the user's timezone.
    start_week = start_local_date - timedelta(days=start_local_date.weekday())
    current_week = local_today - timedelta(days=local_today.weekday())
    weeks_participated = ((current_week - start_week).days // 7) + 1
    weeks_participated = max(1, weeks_participated)

    start_of_week = local_today - timedelta(days=local_today.weekday())
    daily_stats = []
    event_stats = []

    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        day_start_ts, day_end_ts = local_day_bounds_to_utc_timestamps(current_day, user_tz)

        daily_count = count_completed_records(DailyResponse, user_id, day_start_ts, day_end_ts)
        event_count = count_completed_records(EventResponse, user_id, day_start_ts, day_end_ts)
        daily_stats.append(daily_count > 0)
        event_stats.append(str(event_count) if event_count > 0 else '')

    today_start_ts, tomorrow_start_ts = local_day_bounds_to_utc_timestamps(local_today, user_tz)
    daily_completed_today = count_completed_records(
        DailyResponse, user_id, today_start_ts, tomorrow_start_ts
    ) > 0

    return {
        "weeks_participated": weeks_participated,
        "daily_stats": daily_stats,
        "event_stats": event_stats,
        "daily_completed_today": daily_completed_today,
    }
