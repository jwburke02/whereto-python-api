from flask import Flask
from flask import request
from utils import sign_url
import requests
import config
import math
import numpy as np
import json

app = Flask(__name__)

def generate_base_heading(dy, dx):
    base_heading = math.atan2(dy, dx) * 180 / 3.1415
    if base_heading < 0:
        base_heading = 360 + base_heading
    return base_heading

def store_image(idx, surl):
    img = requests.get(surl).content
    with open("images/image" + str(idx) + ".jpg", 'wb') as handler:
        handler.write(img)
    return

def write_images(point_list):
    '''
        point_list is a regular array of arrays
    '''
    idx = 0
    for outer in point_list:
        for inner in outer:
            store_image(idx, inner)
            idx += 1
    return

@app.route("/health")
def health_endpoint():
    return "API is healthy."

@app.route("/query_and_download")
def test_cloud_vision():
    '''
        test_cloud_vision is an endpoint that will take in 2 (x,y) points in the params
        EXAMPLE POINT:
            RANDOM STRETCH ON ST MARYS STREET
            # provided road start and stop
                initial_x = 42.348444
                initial_y = -71.1069238
                final_x = 42.347162
                final_y = -71.1071453
        it will then query the Google Street View API to get images between these points of the street
        The images will collect 8 images for each point, one every 45 degrees
    '''
    # retrieve variables from request URL
    xi = float(request.args.get('xi'))
    xf = float(request.args.get('xf'))
    yi = float(request.args.get('yi'))
    yf = float(request.args.get('yf'))
    call_static_image_api = int(request.args.get('call_maps'))
    # retrieve the API_KEY from the configuration module
    API_KEY = config.map_api_key
    # here is the BASE_URL that we will call
    BASE_URL = "https://maps.googleapis.com/maps/api/streetview"
    # we are calculating the distance (in degrees) that is travelled between these coordinates
    d = math.sqrt((xf - xi) * (xf - xi) + (yf - yi) * (yf - yi))
    # this coefficient can be changed later
    steps = int(d * 8000)
    # now we calculate the distance of each step (for easy iteration)
    dx = (xf - xi) / steps
    dy = (yf - yi) / steps
    # now we calculate the forward heading of this vector
    base_heading = generate_base_heading(dy, dx)
    # really quickly we create a list of headings to take pictures of
    headings = [base_heading]
    for _ in range(7):
        base_heading = base_heading + 45
        if base_heading > 360:
            base_heading = base_heading - 360
        headings.append(base_heading)
    # quickly we prepare the other aspects of the URL
    size = "?size=640x640"
    pitch = "&pitch=0"
    fov = "&fov=80"
    api = "&key=" + API_KEY
    # here is a variable we will store the API links in
    point_list = []
    for count in range(steps + 1):
        x = xi + count * dx
        y = yi + count * dy
        # location parameter construction 
        location = "&location=" + str(x) + "," + str(y) 
        # we make a seperate api request for each heading
        link_list = []
        for heading in headings:
            query = sign_url(BASE_URL + size + location + pitch + fov + "&heading=" + str(heading) + api)
            link_list.append(query)
        point_list.append(link_list)
    if(call_static_image_api):
        write_images(point_list)
    return [200]

@app.route("/use_vision_example")
def detect_labels():
    """Detects labels in the file."""
    from google.cloud import vision

    client = vision.ImageAnnotatorClient()

    with open("images/image66.jpg", "rb") as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.label_detection(image=image)
    labels = response.label_annotations
    print("Labels:")

    for label in labels:
        print(label.description)

    if response.error.message:
        raise Exception(
            "{}\nFor more info on error messages, check: "
            "https://cloud.google.com/apis/design/errors".format(response.error.message)
        )
    
    return [200]