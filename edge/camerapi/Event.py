from PIL import Image
import json
import io
import base64
from numpy import ndarray

class Event:
    def __init__(self, timestamp: str, image: ndarray, person_count: int):
        self.timestamp = timestamp
        self.image = Image.fromarray(image)
        self.person_count = person_count

    def message_data(self):
        return json.dumps({
            "timestamp": self.timestamp,
            "person_count": self.person_count
        })

    def get_image_buffer(self):
        image_buffer = io.BytesIO()
        self.image.save(image_buffer, format="JPEG")
        image_buffer.seek(0)
        return image_buffer
