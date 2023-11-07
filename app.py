from flask import Flask
from flask import request
from utils import sign_url
import requests
import config
import math
import numpy as np
import json

app = Flask(__name__)

@app.route("/health")
def health_endpoint():
    return "API is healthy."

@app.route('/get_images', methods=['GET', 'POST'])
def get_images():
    start_x = float(request.args.get('start_x')) # float coordinate x
    end_x = float(request.args.get('end_x')) # float coordinate x
    start_y = float(request.args.get('start_y')) # float coordinate y
    end_y = float(request.args.get('end_y')) # float coordinate y
    distance = math.sqrt(((end_x - start_x)*(end_x - start_x)) + ((end_y - start_y)*(end_y - start_y)))
    steps = int(distance * 10000)
    API_KEY = config.map_api_key
    base_url = "https://maps.googleapis.com/maps/api/streetview"
    x_step = (end_x - start_x) / steps
    y_step = (end_y - start_y) / steps
    base_heading = math.atan2( y_step, x_step ) * 180 / 3.1415
    if base_heading < 0:
        base_heading = 360 + base_heading
    count = 0
    value = {
            "query_list": [],
            "steps": steps
        }
    while count < steps:
        # increment locations
        print("iter")
        temp_x = start_x + count * x_step
        temp_y = start_y + count * y_step
        count = count + 1
        # build the query
        size = "?size=640x640" # max size
        location = "&location=" + str(temp_x) + "," + str(temp_y) # convert locaation to string
        pitch = "&pitch=0" # default to 0 pitch
        fov = "&fov=80" #default fov
        api = "&key=" + API_KEY # for api access
        temp_heading = base_heading
        query = base_url + size + location + str(pitch) + fov + "&heading=" + str(temp_heading) + api
        squery_list_temp = [sign_url(query)]
        for i in range(3):
            temp_heading = temp_heading + 30
            if temp_heading > 360:
                temp_heading = temp_heading - 360
            query = base_url + size + location + str(pitch) + fov + "&heading=" + str(temp_heading) + api
            squery_list_temp.append(sign_url(query))
        print(squery_list_temp)
        value["query_list"].append(squery_list_temp)
    return json.dumps(value)
    


@app.route("/example_query_construct")
def example_image_endpoint():
    final_x = 0
    final_y = 0
    initial_x = 0
    initial_y = 0
    d_xt = final_x - initial_x
    d_yt = final_y - initial_y
    # generates 
    dx = d_xt / 10
    dy = d_yt / 10
    count = 0
    base_heading = math.atan2( d_yt, d_xt ) * 180 / 3.1415
    if base_heading < 0:
        base_heading = 360 + base_heading
    value = {
        "count": count,
        "dy_t": d_yt,
        "dx_y": d_xt,
        "dy": dy,
        "dx": dx,
        "query_list": [],
        "squery_list": []
    }
    while count < 10:
        temp_x = initial_x + count * dx
        temp_y = initial_y + count * dy
        count = count + 1
        # build the query
        size = "?size=640x640"
        location = "&location=" + str(temp_x) + "," + str(temp_y)
        pitch = "&pitch=0"
        api = "&key=" + api_key
        temp_heading = base_heading
        query = base_url + path + size + location + str(pitch) + "&heading=" + str(temp_heading) + api
        query_list_temp = [query]
        squery_list_temp = [sign_url(query)]
        for i in range(5):
            temp_heading = temp_heading + 60
            if temp_heading > 360:
                temp_heading = temp_heading - 360
            query = base_url + path + size + location + str(pitch) + "&heading=" + str(temp_heading) + api
            query_list_temp.append(query)
            squery_list_temp.append(sign_url(query))
        value["query_list"].append(query_list_temp)
        value["squery_list"].append(squery_list_temp)
    return json.dumps(value)

@app.route("/example_image_query")
def example_image_query():
    example_request_url = "https://maps.googleapis.com/maps/api/streetview?size=640x640&location=42.348444,-71.1069238&pitch=0&heading=189.79759061610534&key=AIzaSyBIrPdfIZukUgSFn1eRNsiQMtW5i4mhkTk"
    surl = sign_url(example_request_url)
    res = requests.get(surl).content
    with open('image_name.jpg', 'wb') as handler:
        handler.write(res)
    return [200]
    
@app.route("/download_example_images")
def example_image_download():
    # We start from top of St. Mary to bottom of St. Mary
    # api_key + url + path
    api_key = config.map_api_key
    base_url = "https://maps.googleapis.com"
    path = "/maps/api/streetview"
    # provided road start and stop
    initial_x = 42.348444
    initial_y = -71.1069238
    final_x = 42.347162
    final_y = -71.1071453
    # generate step values
    x_step = (final_x - initial_x) / 10
    y_step = (final_y - initial_y) / 10
