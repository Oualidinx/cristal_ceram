from dotenv import load_dotenv
import os
#
load_dotenv('.env')

class Config:
    LANGUAGES = ['en', 'es']

    @staticmethod
    def init():
        pass
class Development(Config):
    SECRET_KEY = os.environ.get('APP_SECRET_KEY')
    credentials = {
        'driver': 'mysql+pymysql',
        'user': "root",
        'password': ':'+"1091eb5a6c62",
        'host': "localhost",
        'port': 3306,
        'database_name': "cristal_ceram"
    }
    SQLALCHEMY_DATABASE_URI = "{driver}://{user}@{host}:{port}/{database_name}".format(**credentials)

class Testing(Config):
    SECRET_KEY = os.environ.get('APP_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI="sqlite:///cristal_ceram.db"
config = {
    'dev':Development,
    'test':Testing
}