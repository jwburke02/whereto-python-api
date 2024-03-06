import math
import config
from PIL import Image
import requests
import io
from core import model
from multiprocessing.pool import ThreadPool
from services.db import locationExists, getDetections, writeDetection, writeCoordinate
import math

def generate_base_heading(dy, dx):
    base_heading = math.atan2(dy, dx) * 180 / math.pi
    if base_heading < 0:
        base_heading = 360 + base_heading
    return base_heading

def run_query(head_x_y):
    heading = head_x_y['head']
    x = head_x_y['x']
    y = head_x_y['y']
    size = "?size=640x640"
    pitch = "&pitch=0"
    fov = "&fov=80"
    api = "&key=" + config.map_api_key
    location = "&location=" + str(x) + "," + str(y)
    try:
        return [Image.open(io.BytesIO(requests.get("https://maps.googleapis.com/maps/api/streetview" + size + location + pitch + fov + "&heading=" + str(heading) + api).content)), "https://maps.googleapis.com/maps/api/streetview" + size + location + pitch + fov + "&heading=" + str(heading) + api, head_x_y]
    except:
        return None

def run_model(street_coord_list):
    locations = {}
    for street in street_coord_list:
        locations[street] = {
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
                headings = [base_heading + 45]
                for _ in range(3):
                    base_heading = (base_heading + 90) % 360
                    headings.append(base_heading)
                d = math.sqrt((xf - xi) ** 2 + (yf - yi) ** 2)
                steps = int(d * 500)
                steps = steps + 1
                dx = (xf - xi) / steps
                dy = (yf - yi) / steps
                for count in range(steps + 1):
                    y = xi + count * dx
                    x = yi + count * dy
                    print([x, y])
                    locations[street]["coordinates"].append([x, y])
                    cid = locationExists([x, y])
                    if cid is not None:
                        try:
                            detections = getDetections(cid)
                            for detection in detections:
                                temp_list = locations[street]["detections"]
                                already_detected = False
                                for item in temp_list:
                                    if item == detection:
                                        already_detected = True
                                if not already_detected:
                                    locations[street]["detections"].append(detection)
                        except Exception as e:
                            print(e)
                    else:
                        new_cid = writeCoordinate([x, y])
                        count = count + 1 
                        heading_x_ys = []
                        for heading in headings:
                            heading_x_y = {
                                "head": heading,
                                "x": x,
                                "y": y
                            }
                            heading_x_ys.append(heading_x_y)
                        img = []
                        with ThreadPool() as pool:
                            for result in pool.map(run_query, heading_x_ys):
                                img.append(result)
                        for im in img:
                            if im is None:
                                continue
                            results = model.predict(im[0])
                            result = results[0]
                            if len(result.boxes):
                                print("Image Analyzed - Meter Found")
                                for box in result.boxes: # iterate through detections
                                    # we use x (lat) and y (lng) + heading (im[2]['head']) to guess real placement of these objects
                                    w = .00008 # some coordinate offset, about 30ish feet
                                    guessed_lat = x + w * math.cos(im[2]['head'])
                                    guessed_lng = y + w * math.sin(im[2]['head'])
                                    temp = {
                                        "class_name": result.names[box.cls[0].item()],
                                        "lat": guessed_lat,
                                        "lng": guessed_lng,
                                        "conf": box.conf[0].item(),
                                        "image_url": im[1],
                                        "text_read": None
                                    }
                                    if box.conf[0].item() > .7: # only write if were confident
                                        writeDetection(temp, new_cid)
                                        locations[street]["detections"].append(temp)
                            else:
                                print("Image Analyzed - Meter Not Found")
                                continue
    return locations