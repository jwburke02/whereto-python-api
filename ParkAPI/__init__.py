from flask_restful import Resource, reqparse
import config
import requests
from OSM import query_osm
from MachineLearning import run_model
import logging
from math import *

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

parser = reqparse.RequestParser() # to parse JSON request
parser.add_argument('address', required=True, help="Address may not be blank...")
parser.add_argument('radius', required=True, help="Radius cannot be blank...")

def distance(lat1, lng1, lat2, lng2):
    """
    Calculate the distance between two points on the Earth's surface
    using the Haversine formula.
    """
    # Radius of the Earth in kilometers
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat1 = radians(lat1)
    lng1 = radians(lng1)
    lat2 = radians(lat2)
    lng2 = radians(lng2)

    # Calculate the change in coordinates
    dlng = lng2 - lng1
    dlat = lat2 - lat1

    # Calculate the distance using the Haversine formula
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlng / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c

    print(distance)
    return distance

def cleanupLocations(examined_locations):
    for street in examined_locations:
        # print(examined_locations[street])
        if street == 'center_lat' or street == 'center_lng' or street == 'radius':
            continue
        # print(street)
        to_remove = []
        for i, detection1 in enumerate(examined_locations[street]['detections']):
            for other_street in examined_locations:
                if other_street == 'center_lat' or other_street == 'center_lng' or other_street == 'radius':
                    continue
                # print(examined_locations[other_street])
                to_remove = []
                time_to_leave = False
                for j, detection2 in enumerate(examined_locations[other_street]['detections']):
                    if j != i:
                        if distance(detection1['lat'], detection1['lng'], detection2['lat'], detection2['lng']) < .0035:
                            print("REMOVED DIST")
                            to_remove.append(i)
                            time_to_leave = True
                            break
                if time_to_leave:
                    break # get a new iter
            for ind in to_remove:
                examined_locations[street]['detections'].pop(ind)
                for iter, val in enumerate(to_remove):
                    to_remove[iter] = val - 1
    return examined_locations

class ParkAPI(Resource):
    def post(self):
        try:
            ######################################
            # BEGIN ERROR CHECKING OF PARAMETERS #
            ######################################
            args = parser.parse_args()
            radius = float(args['radius'])
            address = args['address']
            logging.info("Received request -- Address: " + address + "; Radius: " + str(radius))
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
            if long is None or lat is None:
                return "Parameter Error: Issue with locating address", 500
            ################## MAP DATA QUERY ##################
            street_coord_list = query_osm(lat, long, radius)
            ################## ML ######################
            examined_locations = run_model(street_coord_list, lat, long, radius)
            examined_locations['radius'] = radius
            examined_locations['center_lat'] = lat
            examined_locations['center_lng'] = long
            examined_locations = cleanupLocations(examined_locations)
            return examined_locations
        except Exception as e:
            logger.debug(e)
            return "Error with your request...", 500