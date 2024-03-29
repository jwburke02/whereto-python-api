import base64
from WhereTo import db
from random import randint
import requests
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

################### MODEL DEFINITION #######################
class coordinate(db.Model):
    cid = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)

    def __init__(self, cid, lat, lng):
        self.cid = cid
        self.lat = lat
        self.lng = lng

    def __repr__(self) -> str:
        return super().__repr__()


class detection(db.Model):
    did = db.Column(db.Integer, primary_key=True)
    cid = db.Column(db.Integer, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    class_name = db.Column(db.String, nullable=False)
    conf = db.Column(db.Float, nullable=False)
    text_read = db.Column(db.String, nullable=True)
    image_url = db.Column(db.String, nullable=False)

    def __init__(self, did, cid, lat, lng, class_name, conf, text_read, image_url):
        self.cid = cid
        self.did = did
        self.lat = lat
        self.lng = lng
        self.class_name = class_name
        self.conf = conf
        self.text_read = text_read
        self.image_url = image_url

    def __repr__(self) -> str:
        return super().__repr__()

###################### END MODEL DEFINITION #######################

####################### DATABASE ACCESS FUNCTIONALITY #####################
def locationExists(point): # function that will return if a point exists in our database yet
    try:
        result = coordinate.query.filter_by(lat=point[0], lng=point[1]).first()
        if (result):
            return result.cid # the coordinate has been analyzed and is in DB
        else:
            return None
    except: 
        return None

def getDetections(cid): # function that will get every detection for a given CID in the database
    try:
        detections = []
        results = detection.query.filter_by(cid=cid)
        for result in results:
            new_result = {
                "did": result.did,
                "class_name": result.class_name,
                "lat": result.lat,
                "lng": result.lng,
                "conf": result.conf,
                "text_read": result.text_read,
                "image_url": None
            }
            detections.append(new_result)
        return detections
    except Exception as e:
        logger.debug(e)
    
def writeCoordinate(point): # function taht will write a new coordinate to the database
    min = 1
    max = 100000000
    rand = randint(min, max)
    while detection.query.filter_by(did=rand).limit(1).first() is not None:
        rand = randint(min, max)
    # now rand is our id
    new_coord = coordinate(rand, point[0], point[1])
    db.session.add(new_coord)
    db.session.commit()
    return rand

    
def writeDetection(data, cid): # function that will write a new detection to the database
    min = 1
    max = 100000000
    rand = randint(min, max)
    while detection.query.filter_by(did=rand).limit(1).first() is not None:
        rand = randint(min, max)
    # now rand is our id
    new_detect = detection(rand, cid, data['lat'], data['lng'], data['class_name'], data['conf'], data['text_read'], data['image_url'])
    db.session.add(new_detect)
    db.session.commit()
    data['did'] = rand
    data['image_url'] = None
    return data

def readDetection(did): # function that returns detailed information for a DID in the database
    try:
        results = detection.query.filter_by(did=did)
        for result in results:
            to_query = result.image_url
            image_data = requests.get(to_query).content
            base64_string = base64.b64encode(image_data)
            im = base64_string.decode('utf-8')
            new_result = {
                "did": result.did,
                "class_name": result.class_name,
                "lat": result.lat,
                "lng": result.lng,
                "conf": result.conf,
                "text_read": result.text_read,
                "image_data": im
            }
            return new_result
    except Exception as e:
        logger.debug(e)

####################### END DATABASE ACCESS FUNCTIONALITY #####################