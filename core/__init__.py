from flask import Flask
from ultralytics import YOLO
from flask_restful import Api

app = Flask(__name__)
api = Api(app)
meters = YOLO("meters.pt")