from flask_sqlalchemy import SQLAlchemy
from time import strftime, gmtime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.String(32))
    password = db.Column(db.String(128))

    def __init__(self, userid=None, password=None):
        self.userid = userid
        self.password = password


class Images(db.Model):
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(128))
    datetime = db.Column(db.DateTime)
    pose = db.Column(db.String(128))

    def __init__(self, datetime=None, pose=None, path = None):
        self.datetime = datetime
        self.pose = pose
        self.path = path

    @property
    def serialized(self):
        """Return object data in serializeable format"""
        return {
            'path': self.path,
            'datetime': str(self.datetime),
            'pose':self.pose,
        }