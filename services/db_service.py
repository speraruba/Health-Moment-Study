from contextlib import closing

import mysql.connector
from mysql.connector import errorcode

from models import User
from services.time_service import current_utc_timestamp

# Local version
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='Health_Moment',
        use_unicode=True,
        auth_plugin='mysql_native_password',
        charset='utf8mb4',
    )

#DEPLOY VERSION
# def get_db_connection():
#     return mysql.connector.connect(
#         host='localhost',
#         user='cogsearch_hugo',
#         password='tQf]$%%(QQ!GZb;r',
#         database='cogsearch_health_moment',
#         use_unicode=True,
#         auth_plugin='mysql_native_password',
#         charset='utf8mb4',
#     )


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
            screening_completed BOOLEAN NOT NULL DEFAULT 0,
            baseline_completed BOOLEAN NOT NULL DEFAULT 0
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


def get_user_by_id(user_id):
    return User.from_row(fetch_one("SELECT * FROM users WHERE user_id = %s", (user_id,)))


def create_user(user_id, username):
    start_date = current_utc_timestamp()
    try:
        execute(
            """
            INSERT INTO users (user_id, username, start_date, screening_completed, baseline_completed)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, username, start_date, False, False),
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
    execute(
        f"""
        INSERT INTO {table_name} (user_id, response_id, status, timestamp)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, response_id, status, response_timestamp),
    )


def insert_response_if_new(table_name, user_id, response_id, status, response_timestamp):
    return execute_with_rowcount(
        f"""
        INSERT IGNORE INTO {table_name} (user_id, response_id, status, timestamp)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, response_id, status, response_timestamp),
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
