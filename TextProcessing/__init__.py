from google.cloud import vision
client = vision.ImageAnnotatorClient()

def detect_text(content):
    """Detects text in the file."""
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    response = ""
    for iter, text in enumerate(texts):
        if iter != len(texts) - 1:
            response += (text.description + ' ')
    return response