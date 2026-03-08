from flask import Flask

from blueprints.auth import bp as auth_bp
from blueprints.dashboard import bp as dashboard_bp
from blueprints.webhook import bp as webhook_bp
from extensions import db
from services.db_service import ensure_users_completion_columns


def create_app():
    app = Flask(__name__)
    app.secret_key = 'your_secret_key_here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost:3306/Health_Moment'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(webhook_bp)

    with app.app_context():
        db.create_all()
        ensure_users_completion_columns()

    return app


app = create_app()


if __name__ == '__main__':
    app.run(port=5001, debug=True)

