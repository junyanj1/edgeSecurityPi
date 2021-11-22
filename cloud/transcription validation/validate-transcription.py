import base64
from Crypto.Cipher import AES

from google.cloud import iot_v1
from google.api_core.exceptions import NotFound, FailedPrecondition

PASSWORD = "hello" # change password here
COMMON_ENCRYPTION_KEY=''
COMMON_16_BYTE_IV_FOR_AES='IVIVIVIVIVIVIVIV'

project_id = 'engaged-purpose-277720'
cloud_region = 'us-central1'
registry_id = 'Team5-PiLock'
device_id = 'camera-1'
version = 0

SAVE_IMAGE = "1"
DO_NOT_SAVE_IMAGE = "0"


def get_common_cipher():
    return AES.new(COMMON_ENCRYPTION_KEY,
                   AES.MODE_CBC,
                   COMMON_16_BYTE_IV_FOR_AES)

def decrypt_message(ciphertext):
    common_cipher = get_common_cipher()
    raw_ciphertext = base64.b64decode(ciphertext)
    decrypted_message_with_padding = common_cipher.decrypt(raw_ciphertext)
    return decrypted_message_with_padding.decode('utf-8').strip()

def validateTranscription(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    # Ignore all devices except VoicePi
    if (event['attributes']['deviceId'] != "microphone-1"):
        return

    encrypted_transcription = base64.b64decode(event['data']).decode('utf-8')
    transcription = decrypt_message(encrypted_transcription)
    print(transcription)
    success = transcription.lower() == PASSWORD

    if success:
        print(DO_NOT_SAVE_IMAGE)
        publish(DO_NOT_SAVE_IMAGE)
    else:
        print(SAVE_IMAGE)
        publish(SAVE_IMAGE)

def publish(config):
    print('Set device configuration')
    client = iot_v1.DeviceManagerClient()
    device_path = client.device_path(project_id, cloud_region, registry_id, device_id)

    data = config.encode('utf-8')

    try:
        client.send_command_to_device(device_path,data)
    except NotFound:
        print(f"Device {device_id} does not exist or is not subscribed to command topic.")
    except FailedPrecondition:
        print(f"Device {device_id} is offline.")
