import os
import telnyx
import logging
import requests
import urllib.parse

def send_alert(event, context):
     GCP_STORAGE_PREFIX = "https://storage.cloud.google.com/"
     TO_PHONE_NUMER = os.getenv("TO_PHONE_NUMBER") # TODO: Database.
     FROM_PHONE_NUMBER = os.getenv("FROM_PHONE_NUMBER")

     telnyx.api_key = os.getenv("TELNYX_API")
     
     try:
          image_url = urllib.parse.quote(f"{GCP_STORAGE_PREFIX}{event['bucket']}/{event['name']}")
          short_url_response = requests.get(f"https://api.urlday.com/short?url={image_url}")
          short_url = short_url_response.json()["result"]
          
          telnyx.Message.create(
               from_=FROM_PHONE_NUMBER,
               to=TO_PHONE_NUMER,
               text=f"A person has been detected with an incorrect password!\nImage: {short_url}",
          )
     except Exception as e:
          logging.exception(e)
          print("Something went wrong sending the message.")
