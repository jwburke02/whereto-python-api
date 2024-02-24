# OSM helper functions + main extract pipeline
import config
import math
import requests

def map_geo_data(old_data):
    new_data = {} # we are going to index by street
    for point in old_data:
        street_name = point.get("properties").get("name")
        if street_name is None:
            continue
        if new_data.get(street_name) is None: # first time seeing street
            if point.get("geometry").get("coordinates") is not None:
                new_data[street_name] = point.get("geometry").get("coordinates")[0]
        else: # here we have to append to existing street info
            temp_list = new_data.get(street_name)
            if point.get("geometry").get("coordinates") is not None:
                temp_list.extend(point.get("geometry").get("coordinates")[0])
            new_data[street_name] = temp_list
    # we have street level data, place coordinates in the correct order:
    street_source = {}
    street_coord_list = {}
    for street in new_data:
        coordinate_list = new_data[street]
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
    
    return street_coord_list

def query_osm(lat, lng, rad):
    degpermile_lat = 1 / 69.172 # conventional conversion rate of lat to miles
    degpermile_lng = 1 / (69.172 * math.cos(math.radians(lat))) # conventional conversion rate of lng to miles given lat
    off_lng = degpermile_lng * rad
    off_lat = degpermile_lat * rad
    bottom = lat - off_lat
    top = lat + off_lat
    left = lng - off_lng
    right = lng + off_lng
    # DEBUG
    print("Degrees Per Mile (LAT): " + str(degpermile_lat))
    print("Degrees Per Mile (LONG): " + str(degpermile_lng))
    print("Bounds: " + str(left) + " " + str(top) + " " + str(right) + " " + str(bottom))
    # /DEBUG
    bbox = str(left) + ',' + str(bottom) + ',' + str(right) + ',' + str(top)
    geo_data_params = {
        "api_key": config.osm_extract_key,
        "bbox": bbox,
        "tags": "highway=*" 
    }
    # this returned function will map the response to something more usable by our ParkAPI
    return map_geo_data(requests.get(config.osm_extract_http, params=geo_data_params).json().get("features"))
'''
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
'''