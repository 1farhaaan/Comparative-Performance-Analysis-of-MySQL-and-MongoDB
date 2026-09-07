from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import pymongo
import os

csrf = CSRFProtect()

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please sign in to access this page.'
login_manager.login_message_category = 'error'

mongo_client = None
mongo_db = None

def init_mongo(app):
    """Connect PyMongo and store db reference on app."""
    global mongo_client, mongo_db
    mongo_client = pymongo.MongoClient(os.getenv('MONGO_URI'))
    mongo_db = mongo_client['tickets']
    mongo_col = mongo_db['complaint_tickets']
    app.mongo_db = mongo_db   # also attach to app for easy access in routes
    #    return mongo_db




# See PyCharm help at https://www.jetbrains.com/help/pycharm/
