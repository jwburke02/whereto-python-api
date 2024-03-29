from google.cloud import vision
client = vision.ImageAnnotatorClient()

def detect_text(content):
    """Detects text in the file."""
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    if len(texts) > 0:
        response = texts[0].description
    else:
        response = "Unable to read text from sign."
    return response