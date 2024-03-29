from DatabaseAccess import readDetection
import requests
import config
from flask_restful import Resource, reqparse
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DetailAPI(Resource):
    def post(self): # endpoint delivers detailed information to the caller
        try:
            new_parser = reqparse.RequestParser()
            new_parser.add_argument('did', required=True, help="DID may not be blank...").add_argument('lat', required=True, help="lat may not be blank...").add_argument('lng', required=True, help="lng may not be blank...")
            args = new_parser.parse_args()
            did = int(args['did'])
            lat = args['lat']
            lng = args['lng']
            result = readDetection(did)
            response = requests.get(f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={config.map_api_key}")
            result['address'] = response.json()['results'][0]['formatted_address']
            return result
        except Exception as e:
            logger.debug(e)
            return "Error with your request...", 500