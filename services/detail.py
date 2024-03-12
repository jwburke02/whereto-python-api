from services.db import readDetection
from flask_restful import Resource, reqparse

class DetailAPI(Resource):
    def post(self):
        try:
            new_parser = reqparse.RequestParser() # to parse JSON request
            new_parser.add_argument('did', required=True, help="DID may not be blank...")
            args = new_parser.parse_args()
            did = int(args['did'])
            return readDetection(did)
        except Exception as e:
            print(e)
            return "Error with your request...", 500