from flask_restful import Resource, reqparse
import config
import requests
import math
import json
from core import meters

parser = reqparse.RequestParser() # to parse JSON request
parser.add_argument('address', required=True, help="Address may not be blank...")
parser.add_argument('radius', required=True, help="Radius cannot be blank...")

def generate_base_heading(dy, dx):
    base_heading = math.atan2(dy, dx) * 180 / math.pi
    if base_heading < 0:
        base_heading = 360 + base_heading
    return base_heading

class ParkAPI(Resource):
    def post(self):
        try:
            #
            # BEGIN ERROR CHECKING OF PARAMETERS
            #
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
            #
            # END ERROR CHECKING OF PARAMETERS
            #
            #
            # BEGIN QUERY TO OSM
            #
            degpermile_lat = 1 / 69.172 # conventional conversion rate of lat to miles
            degpermile_lng = 1 / (69.172 * math.cos(math.radians(lat))) # conventional conversion rate of lng to miles given lat
            off_lng = degpermile_lng * radius
            off_lat = degpermile_lat * radius
            bottom = lat - off_lat
            top = lat + off_lat
            left = long - off_lng
            right = long + off_lng
            print("Degrees Per Mile (LAT): " + str(degpermile_lat))
            print("Degrees Per Mile (LONG): " + str(degpermile_lng))
            print("Bounds: " + str(left) + " " + str(top) + " " + str(right) + " " + str(bottom))
            bbox = str(left) + ',' + str(bottom) + ',' + str(right) + ',' + str(top)
            hwy_list = ["primary", "secondary", "tertiary", "residential", "living_street", "road", "trunk"]
            geo_data_response = {}
            for hwy in hwy_list:
                tags = "highway=" + hwy
                geo_data_params = {
                    "api_key": config.osm_extract_key,
                    "bbox": bbox,
                    "tags": tags 
                }
                response = requests.get(config.osm_extract_http, params=geo_data_params).json().get("features")
                geo_data_response[hwy] = response
            #
            # END QUERY TO OSM
            #
            #
            # BEGIN MAP RESPONSE TO STREET DICT
            #
            street_dict = {}
            for key in geo_data_response:
                osm_point_list = geo_data_response[key]
                for point in osm_point_list:
                    street_name = point.get("properties").get("name")
                    if street_name is None:
                        continue
                    if street_dict.get(street_name) is None:
                        if point.get("geometry").get("coordinates") is not None:
                            street_dict[street_name] = point.get("geometry").get("coordinates")[0]
                    else: # here we have to append to existing
                        temp_list = street_dict.get(street_name)
                        if point.get("geometry").get("coordinates") is not None:
                            temp_list.extend(point.get("geometry").get("coordinates")[0])
                        street_dict[street_name] = temp_list
            #
            # END MAP RESPONSE TO STREET DICT
            #
            #
            # BEGIN EVALUATE PROPER COORDINATE ORDER
            #
            street_source = {}
            street_coord_list = {}
            for street in street_dict:
                coordinate_list = street_dict[street]
                # EVALUATE EVERY DISTANCE
                dist_mat = []
                for coordinate_pair in coordinate_list:
                    dist_vec = []
                    for inner_pair in coordinate_list:
                        dist_vec.append(math.sqrt(math.pow(coordinate_pair[0]-inner_pair[0],2) + math.pow(coordinate_pair[1]-inner_pair[1],2)))
                    dist_mat.append(dist_vec)
                # USE DIST_MAT MAX INDICES AS SOURCES
                max_list = []
                for idx, _ in enumerate(coordinate_list):
                    dist_row = dist_mat[idx]
                    max_list.append(max(dist_row))
                source_idx = max_list.index(max(max_list))
                street_source[street] = (source_idx, coordinate_list[source_idx])
                street_coord_in_order = []
                source = street_source[street][0]
                count = 0
                while True:
                    if count > 200: # should never be here
                        break
                    count += 1
                    street_coord_in_order.append(coordinate_list[source])
                    coord = coordinate_list[source]
                    coordinate_list.pop(source)
                    d = []
                    if(len(coordinate_list) == 0):
                        break
                    for pair in coordinate_list:
                        d.append(math.sqrt(math.pow(pair[0]-coord[0],2) + math.pow(pair[1]-coord[1],2)))
                    source = d.index(min(d))
                street_coord_list[street] = street_coord_in_order   
            #
            # END EVALUATE PROPER COORDINATE ORDER
            #
            ################## ML ######################
            examined_locations = {}
            size = "?size=640x640"
            pitch = "&pitch=0"
            fov = "&fov=80"
            for street in street_coord_list:
                examined_locations[street] = {
                    "coordinates": [],
                    "detections": []
                }
                
                for idx in range(len(street_coord_list[street])): # iterate through each coordinate in the street segment
                    if idx != len(street_coord_list[street]) - 1:
                        xi = street_coord_list[street][idx][0]
                        xf = street_coord_list[street][idx + 1][0]
                        yi = street_coord_list[street][idx][1]
                        yf = street_coord_list[street][idx + 1][1]
                        dy = yf - yi
                        dx = xf - xi
                        base_heading = generate_base_heading(dy, dx)
                        headings = [base_heading]
                        for _ in range(7):
                            base_heading = (base_heading + 45) % 360
                            headings.append(base_heading)
                        d = math.sqrt((xf - xi) ** 2 + (yf - yi) ** 2)
                        steps = int(d * 500)
                        steps = steps + 1
                        dx = (xf - xi) / steps
                        dy = (yf - yi) / steps
                        api = "&key=" + config.map_api_key
                        for count in range(steps + 1):
                            y = xi + count * dx
                            x = yi + count * dy
                            location = "&location=" + str(x) + "," + str(y)
                            print([x, y])
                            examined_locations[street]["coordinates"].append([x, y])
                            count = count + 1 
                            for heading in headings:
                                img = requests.get("https://maps.googleapis.com/maps/api/streetview" + size + location + pitch + fov + "&heading=" + str(heading) + api).content
                                with open("temp.jpg", 'wb') as handler:
                                    handler.write(img)
                                results = meters.predict("temp.jpg")
                                result = results[0]
                                if len(result.boxes):
                                    print("Image Analyzed - Meter Found")
                                    conf = 0
                                    classifier = ""
                                    for box in result.boxes:
                                        confidence = box.conf[0].item()
                                        if confidence > conf:
                                            conf = confidence
                                            classifier = result.names[box.cls[0].item()]
                                    y = street_coord_list[street][idx][1]
                                    x = street_coord_list[street][idx][0]
                                    temp = {
                                        "class": classifier,
                                        "lat": x,
                                        "lng": y,
                                        "conf": confidence
                                    }
                                    examined_locations[street]["detections"].append(temp)
                                else:
                                    print("Image Analyzed - Meter Not Found")
                                    continue
            print(examined_locations)
            ################## /ML/ ######################
            with open('temp.json', 'w') as fp:
                json.dump(examined_locations, fp)
            return examined_locations
        except Exception as e:
            return {"Error": e}, 500

"""
    PROOF OF CONCEPT: DISPLAY A RED MARKER FOR METER LOCATIONS
"""
"""
markers_string = "size:small|color:purple"
for coords_conf in meter_coord_list:
    markers_string += '|' + (str(coords_conf[1]) + ',' + str(coords_conf[0]))
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
"""
"""
    MAP OUT EVERY VISITED COORDINATE
"""
"""
markers_string = "size:small|color:green"
for location in examined_locations:
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
################################################################
################################################################
"""