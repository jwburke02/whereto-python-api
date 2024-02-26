from flask_restful import Resource, reqparse
import config
import requests
import json
from services.osm import query_osm
from services.ml import run_model
import os

parser = reqparse.RequestParser() # to parse JSON request
parser.add_argument('address', required=True, help="Address may not be blank...")
parser.add_argument('radius', required=True, help="Radius cannot be blank...")

def display_map(radius, lat, long, examined_locations):
    markers_string = "size:small|color:green"
    for street in examined_locations:
        if street == 'radius' or street == 'center_lat' or street == 'center_lng':
            continue
        for location in examined_locations[street]['coordinates']:
            markers_string += '|' + (str(location[0]) + ',' + str(location[1]))
    static_image_params = {
        "key": config.map_api_key,
        "center": (str(lat) + ',' + str(long)),
        "zoom": 16,
        "size": "640x640",
        "scale": 2,
        "markers": markers_string
    }
    img = requests.get("https://maps.googleapis.com/maps/api/staticmap", params=static_image_params).content
    image_dir = "./map"
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    file_path = os.path.join(image_dir, "visited.jpg")
    with open(file_path, 'wb') as handler:
        handler.write(img)

def display_detections(radius, lat, long, examined_locations):
    markers_string = "size:small|color:purple"
    for street in examined_locations:
        if street == 'radius' or street == 'center_lat' or street == 'center_lng':
            continue
        for detection in examined_locations[street]['detections']:
            markers_string += '|' + (str(detection['lat']) + ',' + str(detection['lng']))
    static_image_params = {
        "key": config.map_api_key,
        "center": (str(lat) + ',' + str(long)),
        "zoom": 16,
        "size": "640x640",
        "scale": 2,
        "markers": markers_string
    }
    img = requests.get("https://maps.googleapis.com/maps/api/staticmap", params=static_image_params).content
    image_dir = "./map"
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    file_path = os.path.join(image_dir, "mapexample.jpg")
    with open(file_path, 'wb') as handler:
        handler.write(img)

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
            display_map(radius, lat, long, examined_locations) # debug
            display_detections(radius, lat, long, examined_locations) # debug
            ################## /ML/ ######################
            with open('mock_data/temp.json', 'w') as fp:
                json.dump(examined_locations, fp)
            return examined_locations
        except Exception as e:
            return "Error with your request...", 500