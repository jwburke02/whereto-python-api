from flask import Flask
import os
from ultralytics import YOLO
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), '../database/whereto.db')
db = SQLAlchemy(app)
model = YOLO("model4.pt")