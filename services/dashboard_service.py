from datetime import datetime, timedelta, timezone

from models import DailyResponse, EventResponse
from services.db_service import count_completed_responses as count_completed_rows
from services.time_service import resolve_dashboard_timezone, local_day_bounds_to_utc_timestamps


def count_completed_records(model, user_id, start_ts, end_ts):
    return count_completed_rows(model.table_name, user_id, start_ts, end_ts)


def calculate_current_week(start_local_date, local_today):
    days_since_start = (local_today - start_local_date).days
    full_weeks_elapsed = max(0, days_since_start) // 7
    current_week = full_weeks_elapsed + 1
    current_week_start = start_local_date + timedelta(days=full_weeks_elapsed * 7)
    return current_week, current_week_start


def build_dashboard_context(user, user_id):
    user_tz = resolve_dashboard_timezone()
    local_today = datetime.now(timezone.utc).astimezone(user_tz).date()

    # Use the participant-selected date as the dashboard anchor.
    effective_start_ts = user.calendar_start_date if user.calendar_start_date else user.start_date
    start_local_date = datetime.fromtimestamp(effective_start_ts, timezone.utc).astimezone(user_tz).date()

    weeks_participated, start_of_week = calculate_current_week(start_local_date, local_today)

    daily_stats = []
    event_stats = []
    day_labels = []
    mobile_day_labels = []

    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        day_start_ts, day_end_ts = local_day_bounds_to_utc_timestamps(current_day, user_tz)

        daily_count = count_completed_records(DailyResponse, user_id, day_start_ts, day_end_ts)
        event_count = count_completed_records(EventResponse, user_id, day_start_ts, day_end_ts)
        daily_stats.append(daily_count > 0)
        event_stats.append(str(event_count) if event_count > 0 else '')
        day_labels.append(f"Day {i + 1} ({current_day.strftime('%A')})")
        mobile_day_labels.append(f"Day {i + 1} ({current_day.strftime('%a')})")

    today_start_ts, tomorrow_start_ts = local_day_bounds_to_utc_timestamps(local_today, user_tz)
    daily_completed_today = count_completed_records(
        DailyResponse, user_id, today_start_ts, tomorrow_start_ts
    ) > 0

    return {
        "weeks_participated": weeks_participated,
        "daily_stats": daily_stats,
        "event_stats": event_stats,
        "daily_completed_today": daily_completed_today,
        "day_labels": day_labels,
        "mobile_day_labels": mobile_day_labels,
    }
