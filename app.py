from flask import Flask
from flask_session import Session
from db import close_db
from api import api_bp
from views import views_bp
from auth import auth_bp

from db import close_db

app = Flask(__name__)
app.config["SECRET_KEY"] = "4647586b6f63536f6e65526f596e614a"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.teardown_appcontext(close_db)



app.register_blueprint(api_bp)
app.register_blueprint(views_bp)
app.register_blueprint(auth_bp)

if __name__ == "__main__":
    app.run(debug=True)