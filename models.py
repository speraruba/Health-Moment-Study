from dataclasses import dataclass

from services.time_service import current_utc_timestamp


@dataclass
class User:
    id: int | None = None
    user_id: str = ''
    username: str = ''
    start_date: int = 0
    screening_completed: bool = False
    baseline_completed: bool = False
    screening_id: str | None = None
    baseline_id: str | None = None

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(
            id=row.get('id'),
            user_id=row.get('user_id', ''),
            username=row.get('username', ''),
            start_date=row.get('start_date') or current_utc_timestamp(),
            screening_completed=bool(row.get('screening_completed')),
            baseline_completed=bool(row.get('baseline_completed')),
            screening_id=row.get('screening_id'),
            baseline_id=row.get('baseline_id'),
        )


@dataclass
class DailyResponse:
    table_name = 'daily_responses'


@dataclass
class EventResponse:
    table_name = 'event_responses'
