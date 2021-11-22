from __future__ import print_function

import random
import sys
import socket
import time
from colors import bcolors

from google.cloud import iot_v1
from google.api_core.exceptions import NotFound, FailedPrecondition

class Comm:
    def __init__(self,device_id):
        self.device_id = device_id
        self.ADDR = '' # ip address of comm server
        self.PORT = 10000
        # Create a UDP socket
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = (self.ADDR, self.PORT)
        print('Bringing up device {}'.format(device_id))

    def SendCommand(self,sock, message, log=True):
        """ returns message received """
        if log:
            print('sending: "{}"'.format(message), file=sys.stderr)

        sock.sendto(message.encode('utf8'), self.server_address)

        # Receive response
        if log:
            print('waiting for response', file=sys.stderr)
            response, _ = sock.recvfrom(4096)
        if log:
            print('received: "{}"'.format(response), file=sys.stderr)

        return response

    def MakeMessage(self,device_id, action, data=''):
        if data:
            return '{{ "device" : "{}", "action":"{}", "data" : "{}" }}'.format(
                device_id, action, data)
        else:
            return '{{ "device" : "{}", "action":"{}" }}'.format(device_id, action)

    def RunAction(self,action,data=''):
        message = self.MakeMessage(self.device_id, action, data)
        if not message:
            return
        print('Send data: {} '.format(message))
        event_response = self.SendCommand(self.client_sock, message)
        print('Response {}'.format(event_response))


class PushCommand:
    def __init__(self,device_id):
        self.project_id = 'engaged-purpose-277720'
        self.cloud_region = 'us-central1'
        self.registry_id = 'Team5-PiLock'
        self.target_device_id = device_id
        self.client = iot_v1.DeviceManagerClient()


    def SendCommand(self,command):
        data = command.encode('utf-8')
        device_path = self.client.device_path(
            self.project_id,
            self.cloud_region,
            self.registry_id,
            self.target_device_id)
        try:
            # client.modify_cloud_to_device_config(device_path, data, version)
            self.client.send_command_to_device(device_path,data)
        except NotFound:
            print("Device {} does not exist or is not subscribed to command topic.".format(self.target_device_id))
        except FailedPrecondition:
            print("Device {} is offline.".format(self.target_device_id))

