
from flask import Flask, request
import requests
import config
import math
from ultralytics import YOLO
from PIL import Image
import io

app = Flask(__name__)

meters = YOLO("meters.pt")

def generate_base_heading(dy, dx):
    base_heading = math.atan2(dy, dx) * 180 / math.pi
    if base_heading < 0:
        base_heading = 360 + base_heading
    return base_heading

#################################
### MAIN APPLICATION PIPELINE ###
#################################
@app.route("/park/query_with_location_and_radius")
def query_with_loc_and_rad():
    ###################################
    # ENSURE BOTH PARAMETERS SUPPLIED #
    ###################################
    address = request.args.get("address")
    radius = float(request.args.get("radius"))
    print("Received request -- Address: " + address + "; Radius: " + str(radius))
    if radius is None:
        return "Parameter Error: No radius supplied", 500
    if address is None:
        return "Parameter Error: No radius supplied", 500
    ##########################
    # BOUND CHECK THE RADIUS #
    ##########################
    if radius < .01 or radius > .25:
        return "Parameter Error: radius should be between .01 and .25 miles", 500
    #######################################
    # GEOCODING TO ENSURE ADDRESS CORRECT #
    #######################################
    geocode_params = {
        "key": config.map_api_key,
        "address": address
    }
    response = requests.get("https://maps.googleapis.com/maps/api/geocode/json", params=geocode_params)
    ############################################
    # ASSIGN LAT AND LONG AND ERROR CHECK THEM #
    ############################################
    lat = response.json().get("results")[0].get("geometry").get("location").get("lat")
    long = response.json().get("results")[0].get("geometry").get("location").get("lng")
    print("LAT: " + str(lat))
    print("LONG: " + str(long))
    if long is None or lat is None:
        return "Parameter Error: Issue with locating address", 500
    ###############################
    # CONSTRUCT QUERY TO OSM DATA #
    ###############################
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
    #################
    # UTILIZE QUERY #
    #################
    bbox = str(left) + ',' + str(bottom) + ',' + str(right) + ',' + str(top)
    hwy_list = ["primary", "secondary", "tertiary", "residential"]
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
    ##############################################################################
    # MAP geo_data_response INTO a dict["street name"] = [coordlist of segments] #
    ##############################################################################
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
    ####################################################
    # EVALUATE PROPER COORDINATE ORDER FOR EACH STREET #
    ####################################################
    """
        given a set of coordinates
            find the distance of each coordinate pair with every other coordinate pair
            the largest distance ones will be the source and destination node (pick the first one)
            from the source, iterate to each closest node until you reach the destination node
    """
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
    ##########################################################################################################
    # FOR EACH STREET IN STREET_COORD_LIST, GO DOWN THE STREET BY COORDINATE AND RUN EACH THROUGH ML PROCESS #
    ##########################################################################################################
    size = "?size=640x640"
    pitch = "&pitch=0"
    fov = "&fov=80"
    meter_coord_list = []
    for street in street_coord_list:
        for ind in range(len(street_coord_list[street])):
            if ind % 4 == 0 and ind != len(street_coord_list[street]) - 1:
                dy = street_coord_list[street][ind + 1][1] - street_coord_list[street][ind][1]
                dx = street_coord_list[street][ind + 1][0] - street_coord_list[street][ind][0]
                base_heading = generate_base_heading(dy, dx)
                headings = [base_heading]
                for _ in range(7):
                    base_heading = (base_heading + 45) % 360
                    headings.append(base_heading)
                location = "&location=" + str(street_coord_list[street][ind][1]) + "," + str(street_coord_list[street][ind][0])
                api = "&key=" + config.map_api_key
                for heading in headings:
                    img = requests.get("https://maps.googleapis.com/maps/api/streetview" + size + location + pitch + fov + "&heading=" + str(heading) + api).content
                    image = Image.open(io.BytesIO(img))
                    #with open("temp.jpg", 'wb') as handler:
                    #    handler.write(img)
                    #results = meters.predict("temp.jpg")
                    results = meters.predict(image)
                    result = results[0]
                    if len(result.boxes):
                        print("Image Analyzed - Meter Found")
                        best_conf = 0
                        for box in result.boxes:
                            conf = box.conf[0].item()
                            if conf > best_conf:
                                best_conf = conf
                        y = street_coord_list[street][ind][1]
                        x = street_coord_list[street][ind][0]
                        temp = [x, y, best_conf]
                        meter_coord_list.append(temp)
                    else:
                        print("Image Analyzed - Meter Not Found")
                        continue
            else:
                continue
    print(meter_coord_list)
    return "Success", 200

if __name__ == '__main__':
    app.run(debug=True)

