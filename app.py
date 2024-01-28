from flask import Flask, request
from utils import sign_url
import requests
import config
import math
import os
from google.cloud import vision
import io
import json

app = Flask(__name__)

def generate_base_heading(dy, dx):
    base_heading = math.atan2(dy, dx) * 180 / math.pi
    if base_heading < 0:
        base_heading = 360 + base_heading
    return base_heading

def detect_text(path):
    """Detects text in the file."""
    client = vision.ImageAnnotatorClient()
    with io.open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    detections = []
    for text in texts:
        detection = {
            "description": text.description,
            "bounds": [(vertex.x, vertex.y) for vertex in text.bounding_poly.vertices]
        }
        detections.append(detection)

    if response.error.message:
        raise Exception('{}\nFor more info on error messages, check: https://cloud.google.com/apis/design/errors'.format(response.error.message))
    
    return detections

def store_image_and_detect_text(idx, surl, results):
    img = requests.get(surl).content
    pics_directory = "/Users/muhammadahmadghani/Downloads/pics"
    if not os.path.exists(pics_directory):
        os.makedirs(pics_directory)
    file_path = os.path.join(pics_directory, f"image{idx}.jpg")
    with open(file_path, 'wb') as handler:
        handler.write(img)

    detections = detect_text(file_path)
    results.append({
        "image_path": file_path,
        "detections": detections
    })

def write_images(point_list):
    results = []
    idx = 0
    for outer in point_list:
        for inner in outer:
            store_image_and_detect_text(idx, inner, results)
            idx += 1

    with open('detection_results.json', 'w') as f:
        json.dump(results, f, indent=4)

@app.route("/health")
def health_endpoint():
    return "API is healthy."

def download_street(xi, xf, yi, yf):

    return

@app.route("/gather_image_data")
def gather_image_data():
    '''
        This endpoint requires there to be passed a street name.

        This endpoint requires the initial and final coordinates of a street segment to be passed.
    '''

    xi = float(request.args.get('xi'))
    xf = float(request.args.get('xf'))
    yi = float(request.args.get('yi'))
    yf = float(request.args.get('yf'))
    idx_base = int(request.args.get('idx'))

    API_KEY = config.map_api_key
    BASE_URL = "https://maps.googleapis.com/maps/api/streetview"

    d = math.sqrt((xf - xi) ** 2 + (yf - yi) ** 2)
    steps = int(d * 8000)
    dx = (xf - xi) / steps
    dy = (yf - yi) / steps
    base_heading = generate_base_heading(dy, dx)
    headings = [base_heading]
    for _ in range(7):
        base_heading = (base_heading + 45) % 360
        headings.append(base_heading)

    size = "?size=640x640"
    pitch = "&pitch=0"
    fov = "&fov=80"
    api = "&key=" + API_KEY
    idx = 0

    for count in range(steps + 1):
        x = xi + count * dx
        y = yi + count * dy
        location = "&location=" + str(x) + "," + str(y)
        for heading in headings:
            query = sign_url(BASE_URL + size + location + pitch + fov + "&heading=" + str(heading) + api)
            img = requests.get(query).content
            pics_directory = "../Image Data"
            if not os.path.exists(pics_directory):
                os.makedirs(pics_directory)
            file_path = os.path.join(pics_directory, f"image{idx + idx_base}.jpg")
            idx += 1
            with open(file_path, 'wb') as handler:
                handler.write(img)
                
    return "Images downloaded."

@app.route("/query_and_download")
def test_cloud_vision():
    xi = float(request.args.get('xi'))
    xf = float(request.args.get('xf'))
    yi = float(request.args.get('yi'))
    yf = float(request.args.get('yf'))
    call_static_image_api = int(request.args.get('call_maps'))
    API_KEY = config.map_api_key
    BASE_URL = "https://maps.googleapis.com/maps/api/streetview"
    d = math.sqrt((xf - xi) ** 2 + (yf - yi) ** 2)
    steps = int(d * 8000)
    dx = (xf - xi) / steps
    dy = (yf - yi) / steps
    base_heading = generate_base_heading(dy, dx)
    headings = [base_heading]
    for _ in range(7):
        base_heading = (base_heading + 45) % 360
        headings.append(base_heading)
    size = "?size=640x640"
    pitch = "&pitch=0"
    fov = "&fov=80"
    api = "&key=" + API_KEY
    point_list = []
    for count in range(steps + 1):
        x = xi + count * dx
        y = yi + count * dy
        location = "&location=" + str(x) + "," + str(y)
        link_list = []
        for heading in headings:
            query = sign_url(BASE_URL + size + location + pitch + fov + "&heading=" + str(heading) + api)
            link_list.append(query)
        point_list.append(link_list)
    if call_static_image_api:
        write_images(point_list)
    return "Images processed and text detected."

if __name__ == '__main__':
    app.run(debug=True)

