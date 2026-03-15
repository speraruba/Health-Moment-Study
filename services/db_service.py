import os
from contextlib import closing

import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv

from models import User
from services.time_service import central_datetime_string, current_utc_timestamp

load_dotenv()


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', 'root'),
        database=os.getenv('DB_NAME', 'Health_Moment'),
        port=int(os.getenv('DB_PORT', '3306')),
        use_unicode=True,
        auth_plugin=os.getenv('DB_AUTH_PLUGIN', 'mysql_native_password'),
        charset=os.getenv('DB_CHARSET', 'utf8mb4'),
    )


def fetch_one(query, params=None):
    with closing(get_db_connection()) as connection:
        with closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()


def fetch_all(query, params=None):
    with closing(get_db_connection()) as connection:
        with closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()


def execute(query, params=None):
    with closing(get_db_connection()) as connection:
        with closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute(query, params or ())
            connection.commit()
            return cursor.lastrowid


def execute_with_rowcount(query, params=None):
    with closing(get_db_connection()) as connection:
        with closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute(query, params or ())
            connection.commit()
            return cursor.rowcount


def initialize_database():
    execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL UNIQUE,
            username VARCHAR(100) NOT NULL,
            start_date BIGINT NOT NULL,
            start_date_central_time VARCHAR(19) DEFAULT NULL,
            screening_completed BOOLEAN NOT NULL DEFAULT 0,
            baseline_completed BOOLEAN NOT NULL DEFAULT 0,
            screening_id VARCHAR(100) DEFAULT NULL,
            baseline_id VARCHAR(100) DEFAULT NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS daily_responses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            response_id VARCHAR(100) NOT NULL UNIQUE,
            status VARCHAR(20) NOT NULL,
            timestamp BIGINT NOT NULL,
            central_time VARCHAR(19) DEFAULT NULL,
            CONSTRAINT fk_daily_user_id
                FOREIGN KEY (user_id) REFERENCES users(user_id)
                ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS event_responses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            response_id VARCHAR(100) NOT NULL UNIQUE,
            status VARCHAR(20) NOT NULL,
            timestamp BIGINT NOT NULL,
            central_time VARCHAR(19) DEFAULT NULL,
            CONSTRAINT fk_event_user_id
                FOREIGN KEY (user_id) REFERENCES users(user_id)
                ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )


def ensure_users_completion_columns():
    columns = fetch_all("SHOW COLUMNS FROM users")
    existing_columns = {column['Field'] for column in columns}

    if 'screening_completed' not in existing_columns:
        execute(
            "ALTER TABLE users ADD COLUMN screening_completed BOOLEAN NOT NULL DEFAULT 0"
        )
    if 'baseline_completed' not in existing_columns:
        execute(
            "ALTER TABLE users ADD COLUMN baseline_completed BOOLEAN NOT NULL DEFAULT 0"
        )
    if 'screening_id' not in existing_columns:
        execute(
            "ALTER TABLE users ADD COLUMN screening_id VARCHAR(100) DEFAULT NULL"
        )
    if 'baseline_id' not in existing_columns:
        execute(
            "ALTER TABLE users ADD COLUMN baseline_id VARCHAR(100) DEFAULT NULL"
        )
    if 'start_date_central_time' not in existing_columns:
        execute(
            "ALTER TABLE users ADD COLUMN start_date_central_time VARCHAR(19) DEFAULT NULL"
        )
    else:
        type_info = next(
            (column for column in columns if column['Field'] == 'start_date_central_time'),
            None,
        )
        if type_info and str(type_info.get('Type', '')).lower() != 'varchar(19)':
            execute(
                "ALTER TABLE users MODIFY COLUMN start_date_central_time VARCHAR(19) DEFAULT NULL"
            )

    rows = fetch_all("SELECT user_id, start_date FROM users")
    for row in rows:
        central_date = central_datetime_string(row['start_date'])
        execute(
            "UPDATE users SET start_date_central_time = %s WHERE user_id = %s",
            (central_date, row['user_id']),
        )


def ensure_response_central_time_columns():
    for table_name in ("daily_responses", "event_responses"):
        columns = fetch_all(f"SHOW COLUMNS FROM {table_name}")
        existing_columns = {column['Field'] for column in columns}
        if 'central_time' not in existing_columns:
            execute(
                f"ALTER TABLE {table_name} ADD COLUMN central_time VARCHAR(19) DEFAULT NULL"
            )
        else:
            type_info = next(
                (column for column in columns if column['Field'] == 'central_time'),
                None,
            )
            if type_info and str(type_info.get('Type', '')).lower() != 'varchar(19)':
                execute(
                    f"ALTER TABLE {table_name} MODIFY COLUMN central_time VARCHAR(19) DEFAULT NULL"
                )

        rows = fetch_all(f"SELECT id, timestamp FROM {table_name}")
        for row in rows:
            central_date = central_datetime_string(row['timestamp'])
            execute(
                f"UPDATE {table_name} SET central_time = %s WHERE id = %s",
                (central_date, row['id']),
            )


def get_user_by_id(user_id):
    return User.from_row(fetch_one("SELECT * FROM users WHERE user_id = %s", (user_id,)))


def create_user(user_id, username):
    start_date = current_utc_timestamp()
    start_date_central_time = central_datetime_string(start_date)
    try:
        execute(
            """
            INSERT INTO users (
                user_id,
                username,
                start_date,
                start_date_central_time,
                screening_completed,
                baseline_completed,
                screening_id,
                baseline_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, username, start_date, start_date_central_time, False, False, None, None),
        )
    except mysql.connector.IntegrityError as exc:
        if exc.errno != errorcode.ER_DUP_ENTRY:
            raise
    return get_user_by_id(user_id)


def update_username(user_id, username):
    execute("UPDATE users SET username = %s WHERE user_id = %s", (username, user_id))
    return get_user_by_id(user_id)


def update_user_completion(user_id, field_name, completed=True):
    if field_name not in {'screening_completed', 'baseline_completed'}:
        raise ValueError(f'Unsupported field: {field_name}')
    execute(
        f"UPDATE users SET {field_name} = %s WHERE user_id = %s",
        (completed, user_id),
    )
    return get_user_by_id(user_id)


def update_user_survey_status(user_id, survey_type, status, response_id):
    if survey_type not in {'screening', 'baseline'}:
        raise ValueError(f'Unsupported survey type: {survey_type}')
    completed = status == 'completed'
    if not completed:
        return get_user_by_id(user_id)
    completed_field = f"{survey_type}_completed"
    id_field = f"{survey_type}_id"
    execute(
        f"UPDATE users SET {completed_field} = %s, {id_field} = %s WHERE user_id = %s",
        (True, response_id, user_id),
    )
    return get_user_by_id(user_id)


def get_or_create_user(user_id, default_username='Unknown_User'):
    user = get_user_by_id(user_id)
    if user:
        return user
    return create_user(user_id, default_username)


def response_exists(table_name, response_id):
    row = fetch_one(
        f"SELECT id FROM {table_name} WHERE response_id = %s",
        (response_id,),
    )
    return row is not None


def insert_response(table_name, user_id, response_id, status, response_timestamp):
    central_date = central_datetime_string(response_timestamp)
    execute(
        f"""
        INSERT INTO {table_name} (user_id, response_id, status, timestamp, central_time)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, response_id, status, response_timestamp, central_date),
    )


def insert_response_if_new(table_name, user_id, response_id, status, response_timestamp):
    central_date = central_datetime_string(response_timestamp)
    return execute_with_rowcount(
        f"""
        INSERT IGNORE INTO {table_name} (user_id, response_id, status, timestamp, central_time)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, response_id, status, response_timestamp, central_date),
    ) == 1


def count_completed_responses(table_name, user_id, start_ts, end_ts):
    row = fetch_one(
        f"""
        SELECT COUNT(*) AS response_count
        FROM {table_name}
        WHERE user_id = %s
          AND timestamp >= %s
          AND timestamp < %s
          AND status = 'completed'
        """,
        (user_id, start_ts, end_ts),
    )
    return int(row['response_count']) if row else 0
