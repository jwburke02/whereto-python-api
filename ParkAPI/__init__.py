from flask_restful import Resource, reqparse
import config
import requests
from OSM import query_osm
from MachineLearning import run_model

parser = reqparse.RequestParser() # to parse JSON request
parser.add_argument('address', required=True, help="Address may not be blank...")
parser.add_argument('radius', required=True, help="Radius cannot be blank...")

class ParkAPI(Resource):
    def post(self):
        try:
            ######################################
            # BEGIN ERROR CHECKING OF PARAMETERS #
            ######################################
            args = parser.parse_args()
            radius = float(args['radius'])
            address = args['address']
            print("Received request -- Address: " + address + "; Radius: " + str(radius))
            if radius is None:
                return {"Error": "Parameter Error: No radius supplied"}, 400
            if address is None:
                return {"Error": "Parameter Error: No address supplied"}, 400
            if radius < .01 or radius > .25:
                return "Parameter Error: radius should be between .01 and .25 miles", 500
            geocode_params = {
                "key": config.map_api_key,
                "address": address
            }
            response = requests.get("https://maps.googleapis.com/maps/api/geocode/json", params=geocode_params)
            lat = response.json().get("results")[0].get("geometry").get("location").get("lat")
            long = response.json().get("results")[0].get("geometry").get("location").get("lng")
            print("LAT: " + str(lat))
            print("LONG: " + str(long))
            if long is None or lat is None:
                return "Parameter Error: Issue with locating address", 500
            ################## MAP DATA QUERY ##################
            street_coord_list = query_osm(lat, long, radius)
            ################## ML ######################
            examined_locations = run_model(street_coord_list)
            examined_locations['radius'] = radius
            examined_locations['center_lat'] = lat
            examined_locations['center_lng'] = long
            return examined_locations
        except Exception as e:
            print(e)
            return "Error with your request...", 500