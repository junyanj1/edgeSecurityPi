from edgetpu.detection.engine import DetectionEngine
import cv2
import imutils
from imutils.video import VideoStream
import time
from PIL import Image
from functools import reduce
from Event import Event
import datetime
from google.cloud import storage
from uuid import uuid4
import logging

from comm_mod import Comm, PushCommand
import sys

IOT_CONFIG = {
    "project_id": "engaged-purpose-277720",
    "cloud_region": "us-central1",
    "registry_id": "Team5-PiLock",
    "device_id": "camera-1"
}

target_device_id = "microphone-1"

CONFIDENCE_THRESHOLD = 0.8
# Will hold the event information so it can be saved if needed.
last_event = None

# Loads the object detection model into the TPU.
model = DetectionEngine("mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite")

# Camera video stream for video capture.
video_stream = VideoStream(usePiCamera=True).start()

# Wait for everything to initialize.
time.sleep(10)
print("Ready.")


def handle_image(event: Event, mqtt_response: str) -> None:
    """
    Determines whether to save the image or not.
    0 = Validation success, do not save.
    1 = Validation failed, save image.
    """
    if mqtt_response == "1":
        try:
            print("Saving image...")
            storage_client = storage.Client()
            storage_bucket = storage_client.bucket("person_detection_events")
            image_name = f"images/{event.timestamp}_{uuid4().hex}.jpeg"
            # image_name = f"images/{uuid4().hex}.jpeg"
            storage_bucket.blob(image_name).upload_from_file(event.get_image_buffer(), content_type="image/jpeg")
            storage_bucket.blob(image_name).make_public()
            image_url = storage_bucket.blob(image_name).public_url
            print(f"Saved image to: {image_url}")
            return image_url
        except Exception as e:
            logging.exception(e)

    print("Image not being saved.")

while True:
    # Do nothing while waiting on the rest of the edge devices to complete their tasks.
    # Empty in-case there is anything left over.
    last_event = None

    current_image = video_stream.read()

    # Decrease image size for faster processing.
    processed_image = imutils.resize(current_image, width=500)

    # Do some processing on the image before running it through the model.
    processed_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
    processed_image = Image.fromarray(processed_image)

    # Run the processed image through the model.
    image_results = model.detect_with_image(processed_image,
                                         threshold=CONFIDENCE_THRESHOLD,
                                         keep_aspect_ratio=True,
                                         relative_coord=False)

    if len(image_results) == 0:
        # Found nothing, continue searching.
        continue

    # Assumes we're only doing one object classification (human).
    total_people = reduce(lambda count, value : count + 1 if value.label_id == 0 else count, image_results, 0)

    if total_people > 0:
        print(f"Total People Found: {total_people}")
        last_event = Event(
            datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat(),
            current_image,
            total_people
        )
        #######################################
        pc = PushCommand(target_device_id)
        command = "ON"
        pc.SendCommand(command)

        cm = Comm(IOT_CONFIG["device_id"])
        try:
            cm.RunAction('detach')
            cm.RunAction('attach')
            cm.RunAction('event',"Person detected")
            cm.RunAction('subscribe')
            config_response = cm.client_sock.recv(4096).decode('utf8')
            print("Waiting for release to continue detection...")
            response = ''
            t_end = time.time() + 90 # wait for response for at most 90 sec
            while time.time() < t_end and response=='':
                response = cm.client_sock.recv(4096).decode('utf8') # Supposedly coming back from another edge device
                print('camera-1 received {}'.format(response))

                handle_image(last_event, response)
        except Exception as e:
            print("exception: {}".format(e))
            print('closing socket', file=sys.stderr)
            cm.client_sock.close()

        finally:
            print('closing socket', file=sys.stderr)
            cm.client_sock.close()
            print("\n\nResuming detection...")
        #######################################
