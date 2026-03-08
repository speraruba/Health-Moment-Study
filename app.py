from flask import Flask

from blueprints.auth import bp as auth_bp
from blueprints.dashboard import bp as dashboard_bp
from blueprints.webhook import bp as webhook_bp
from services.db_service import ensure_users_completion_columns, get_db_connection, initialize_database


def create_app():
    app = Flask(__name__)
    app.secret_key = 'your_secret_key_here'

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(webhook_bp)

    with app.app_context():
        connection = get_db_connection()
        connection.close()
        initialize_database()
        ensure_users_completion_columns()

    return app


app = create_app()
application = app


if __name__ == '__main__':
    app.run(port=5001, debug=True)
