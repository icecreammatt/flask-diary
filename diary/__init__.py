from diary import defaults
from flask import Flask
from flask.ext.login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flaskext.bcrypt import Bcrypt
from flaskext.markdown import Markdown
import locale

# create application
app = Flask(__name__)

# configuration
app.config.from_object(defaults)
app.config.from_envvar("SETTINGS", silent=True)

locale.setlocale(locale.LC_ALL, app.config["LOCALE"])

# SQLAlchemy
db = SQLAlchemy(app)

# Flask-Login
lm = LoginManager()
lm.setup_app(app)

# Flask Bcrypt (passwords)
bcrypt = Bcrypt(app)

# Flask Markdown
markdown = Markdown(app)

from diary import views, models
