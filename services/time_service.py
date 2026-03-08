from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import request, session


def current_utc_timestamp():
    return int(datetime.now(timezone.utc).timestamp())


def normalize_unix_timestamp(value):
    """Normalize webhook time input to unix timestamp (seconds)."""
    if value is None:
        return current_utc_timestamp()

    if isinstance(value, (int, float)):
        ts = float(value)
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return current_utc_timestamp()

        try:
            ts = float(raw)
        except ValueError:
            iso_raw = raw.replace('Z', '+00:00')
            try:
                dt = datetime.fromisoformat(iso_raw)
            except ValueError:
                return current_utc_timestamp()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.astimezone(timezone.utc).timestamp())
    else:
        return current_utc_timestamp()

    if ts > 1_000_000_000_000:
        ts = ts / 1000
    return int(ts)


def resolve_dashboard_timezone():
    tz_name = request.args.get('tz', '').strip()
    if tz_name:
        try:
            tz = ZoneInfo(tz_name)
            session['dashboard_timezone'] = tz_name
            return tz
        except ZoneInfoNotFoundError:
            pass

    saved_tz_name = session.get('dashboard_timezone', '')
    if saved_tz_name:
        try:
            return ZoneInfo(saved_tz_name)
        except ZoneInfoNotFoundError:
            session.pop('dashboard_timezone', None)

    return timezone.utc


def local_day_bounds_to_utc_timestamps(local_date, user_tz):
    local_start = datetime.combine(local_date, time.min, tzinfo=user_tz)
    local_end = local_start + timedelta(days=1)
    utc_start_ts = int(local_start.astimezone(timezone.utc).timestamp())
    utc_end_ts = int(local_end.astimezone(timezone.utc).timestamp())
    return utc_start_ts, utc_end_ts

