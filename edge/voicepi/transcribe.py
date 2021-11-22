from __future__ import division

import re
import sys
import time
import socket
import base64
import math

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import pyaudio
from six.moves import queue
from Crypto.Cipher import AES


COMMON_ENCRYPTION_KEY = ''
COMMON_16_BYTE_IV_FOR_AES = 'IVIVIVIVIVIVIVIV'


IOT_CONFIG = {
    "project_id": "engaged-purpose-277720",
    "topic_name": "transcription",
    "cloud_region": "us-central1",
    "registry_id": "Team5-PiLock",
    "device_id": "microphone-1"
}

# Audio recording parameters
RATE = 44100
CHUNK = int(RATE / 10)

# Gateway IP address & port
ADDR = ''
PORT = 10000

# Create a UDP socket
client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = (ADDR, PORT)


language_code = 'en-US'  # a BCP-47 language tag

client = speech.SpeechClient()
config = types.RecognitionConfig(
    encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=RATE,
    language_code=language_code)
streaming_config = types.StreamingRecognitionConfig(
    config=config,
    interim_results=True)


def SendCommand(sock, message):
    print('sending: "{}"'.format(message))
    sock.sendto(message.encode('utf8'), server_address)
    print('waiting for response')
    response, _ = sock.recvfrom(4096)
    print('received: "{}"'.format(response))
    return response


def MakeMessage(action, data=''):
    if data:
        return '{{ "device": "{}", "action": "{}", "data": "{}" }}'.format(
            IOT_CONFIG["device_id"], action, data)
    else:
        return '{{ "device": "{}", "action": "{}" }}'.format(IOT_CONFIG["device_id"], action)


def RunAction(action, data=''):
    message = MakeMessage(action, data)
    if not message:
        return
    event_response = SendCommand(client_sock, message)


def get_common_cipher():
    return AES.new(COMMON_ENCRYPTION_KEY,
                   AES.MODE_CBC,
                   COMMON_16_BYTE_IV_FOR_AES)


def encrypt_message(text):
    common_cipher = get_common_cipher()
    text_length = len(text)
    next_multiple_of_16 = int(16 * math.ceil(text_length/16))
    padded_text = text.rjust(next_multiple_of_16)
    raw_ciphertext = common_cipher.encrypt(padded_text)
    return base64.b64encode(raw_ciphertext).decode('utf-8')


class MicrophoneStream(object):
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()

        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)


def process(responses):
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript

        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + '\r')
            sys.stdout.flush()

            num_chars_printed = len(transcript)

        else:
            message = transcript + overwrite_chars
            num_chars_printed = 0
            return message

def main():
    print('Bringing up device {}'.format(IOT_CONFIG["device_id"]))

    RunAction('detach')
    RunAction('attach')

    while True:
        RunAction('subscribe')

        # Wait for flag command from CameraPi to start recording password
        response = ''
        while response != 'ON':
            response = client_sock.recv(4096).decode('utf8')

        with MicrophoneStream(RATE, CHUNK) as stream:
            audio_generator = stream.generator()
            requests = (types.StreamingRecognizeRequest(audio_content=content)
                        for content in audio_generator)

            print('\nPerson detected! What is the password?\n')

            # Recognize Speech
            responses = client.streaming_recognize(streaming_config, requests)

            # Choose best matching word and publish
            message = process(responses)

            # Encrypt message
            print('Encrypting data: {} '.format(message))
            message = encrypt_message(message)

            # Publish message to trigger Cloud function
            RunAction("event", message)

    print('Closing socket')
    client_sock.close()


if __name__ == '__main__':
    main()

