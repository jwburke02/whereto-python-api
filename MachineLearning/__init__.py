import math
import config
from PIL import Image
import requests
import io
from WhereTo import model
from multiprocessing.pool import ThreadPool
from DatabaseAccess import locationExists, getDetections, writeDetection, writeCoordinate
import math
from TextProcessing import detect_text
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def checkLatLng(lat, lng, center_lat, center_lng, radius):
    degpermile_lat = 1 / 69.172 # conventional conversion rate of lat to miles
    degpermile_lng = 1 / (69.172 * math.cos(math.radians(center_lat))) # conventional conversion rate of lng to miles given lat
    # convert lat, lng to normalized lat, lng
    lat = lat - center_lat
    lng = lng - center_lng
    # now convert to miles
    lat_miles = lat * (1/degpermile_lat)
    lng_miles = lng * (1/degpermile_lng)
    # now check the miles against radius
    if math.sqrt(lat_miles * lat_miles + lng_miles * lng_miles) < radius:
        return True
    return False

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

def run_model(street_coord_list, center_lat, center_lng, radius):
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
                steps = int(d * 250)
                steps = steps + 1
                dx = (xf - xi) / steps
                dy = (yf - yi) / steps
                for count in range(steps + 1):
                    y = xi + count * dx
                    x = yi + count * dy
                    logger.debug([x, y])
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
                                    if detection['conf'] > .75 and checkLatLng(detection['lat'], detection['lng'], center_lat, center_lng, radius):
                                        locations[street]["detections"].append(detection)
                        except Exception as e:
                            logger.debug(e)
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
                                logger.debug("Image Analyzed - Meter Found")
                                classifier = ""
                                conf = 0
                                box_info = None
                                for box in result.boxes: # iterate through detections
                                    if box.conf[0].item() > conf:
                                        conf = box.conf[0].item()
                                        classifier = result.names[box.cls[0].item()]
                                        box_info = box.xyxy.data[0]
                                        norm_info = box.xyxyn.data[0]
                                        size_info = box.xywhn.data[0]
                                # we use x (lat) and y (lng) + heading (im[2]['head']) to guess real placement of these objects
                                w = .00020 # some coordinate offset
                                norm_info = norm_info.numpy()
                                size_info = size_info.numpy()
                                x_norm_disp = ((norm_info[0] + norm_info[2]) / 2.0) - .5
                                norm_size = size_info[3] * size_info[2]
                                guessed_lat = x + w * math.cos(math.radians(im[2]['head']) + x_norm_disp * 1.5)
                                guessed_lng = y + w * math.sin(math.radians(im[2]['head']) + x_norm_disp * 1.5)
                                temp = {
                                    "class_name": classifier,
                                    "lat": guessed_lat,
                                    "lng": guessed_lng,
                                    "conf": conf,
                                    "image_url": im[1],
                                    "text_read": None
                                }
                                # We need to check if the classifier is road sign, if so read text and return
                                if classifier == "Road Sign" and conf > .75:
                                    buffered = io.BytesIO()
                                    left = box_info.data[0].item() - 30
                                    if left < 0:
                                        left = 0
                                    right = box_info.data[2].item() + 30
                                    if right > 640:
                                        right = 640
                                    top = box_info.data[1].item() + 30
                                    if top > 640:
                                        top = 640
                                    bottom = box_info.data[3].item() - 30
                                    if bottom < 0:
                                        bottom = 0
                                    cropped_im = im[0].crop((left, 140, right, 500)) # anything below 500 will read google and block anyways..
                                    cropped_im.save(buffered, format="JPEG")
                                    img_str = buffered.getvalue()
                                    text_read = detect_text(img_str)
                                    temp['text_read'] = text_read
                                if conf > .75 and checkLatLng(temp['lat'], temp['lng'], center_lat, center_lng, radius): # only write if we're confident
                                    locations[street]["detections"].append(writeDetection(temp, new_cid))
                            else:
                                logger.debug("Image Analyzed - Meter Not Found")
                                continue
    return locations