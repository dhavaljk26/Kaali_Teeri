from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os 

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()

def create_app():
    current_path = os.getcwd() + '/instance'
    print(current_path)
    app = Flask(__name__, instance_path=current_path)

    app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    with app.app_context():
        from .models import User

        @login_manager.user_loader
        def load_user(user_id):
            # since the user_id is just the primary key of our user table, use it in the query for the user
            return User.query.get(int(user_id))

        # blueprint for auth routes in our app
        from .auth import auth as auth_blueprint
        app.register_blueprint(auth_blueprint)  

        # blueprint for non-auth parts of app
        from .main import main as main_blueprint
        app.register_blueprint(main_blueprint)

        from .game import app_game as game_blueprint
        app.register_blueprint(game_blueprint)

        from .mindi import mindi as mindi_blueprint
        app.register_blueprint(mindi_blueprint)

    return app