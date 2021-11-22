import base64

PASSWORD = "hello" # change password here; maybe change to an environment var?

def validateTranscription(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    transcription = base64.b64decode(event['data']).decode('utf-8')
    success = transcription.lower() == PASSWORD
    print(success)
    # publish success var to all Pi devices