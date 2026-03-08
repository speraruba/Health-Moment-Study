from sqlalchemy import inspect, text

from extensions import db


def ensure_users_completion_columns():
    inspector = inspect(db.engine)
    existing_columns = {col['name'] for col in inspector.get_columns('users')}

    alter_statements = []
    if 'screening_completed' not in existing_columns:
        alter_statements.append(
            "ALTER TABLE users ADD COLUMN screening_completed BOOLEAN NOT NULL DEFAULT 0"
        )
    if 'baseline_completed' not in existing_columns:
        alter_statements.append(
            "ALTER TABLE users ADD COLUMN baseline_completed BOOLEAN NOT NULL DEFAULT 0"
        )

    for stmt in alter_statements:
        db.session.execute(text(stmt))
    if alter_statements:
        db.session.commit()

