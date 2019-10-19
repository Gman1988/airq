#!/usr/bin/env python3

import argparse
import time
import datetime
import uuid
import serial
import json
import jwt
import sys

from tendo import singleton
import paho.mqtt.client as mqtt

me = singleton.SingleInstance() # will sys.exit(-1) if another instance of this program is already running

# Constants that shouldn't need to be changed
token_life = 60 #lifetime of the JWT token (minutes)

def parse_command_line_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=(
            'Example Google Cloud IoT Core MQTT device connection code.'))
    parser.add_argument(
            '--project_id',
            required=True,
            help='GCP cloud project name')
    parser.add_argument(
            '--registry_id', 
	        required=True, 
	        help='Cloud IoT Core registry id')
    parser.add_argument(
            '--device_id', 
	        required=True, 
	        help='Cloud IoT Core device id')
    parser.add_argument(
            '--interval', 
            type=int,
            default=30, 
	        help='Measurement interval between two samplings')
    parser.add_argument(
            '--private_key_file',
	        default='../.ssh/ec_private.pem',
            help='Path to private key file.')
    parser.add_argument(
            '--algorithm',
            choices=('RS256', 'ES256'),
            default='ES256',
            help='Which encryption algorithm to use to generate the JWT.')
    parser.add_argument(
            '--cloud_region', default='europe-west1', help='GCP cloud region')
    parser.add_argument(
            '--ca_certs',
            default='/home/pi/.ssh/roots.pem',
            help=('CA root from https://pki.google.com/roots.pem'))
    parser.add_argument(
            '--mqtt_bridge_hostname',
            default='mqtt.googleapis.com',
            help='MQTT bridge hostname.')
    parser.add_argument(
            '--mqtt_bridge_port',
            choices=(8883, 443),
            default=8883,
            type=int,
            help='MQTT bridge port.')
    parser.add_argument(
            '--jwt_expires_minutes',
            default=token_life,
            type=int,
            help=('Expiration time, in minutes, for JWT tokens.'))
    return parser.parse_args()


def create_jwt(cur_time, projectID, privateKeyFilepath, algorithmType):
  token = {
      'iat': cur_time,
      'exp': cur_time + datetime.timedelta(minutes=token_life),
      'aud': projectID
  }

  with open(privateKeyFilepath, 'r') as f:
    private_key = f.read()

  return jwt.encode(token, private_key, algorithm=algorithmType) # Assuming RSA, but also supports ECC

def error_str(rc):
    return '{}: {}'.format(rc, mqtt.error_string(rc))

def on_connect(unusued_client, unused_userdata, unused_flags, rc):
    print('on_connect', error_str(rc))

def on_publish(unused_client, unused_userdata, unused_mid):
    print('on_publish')

def createJSON(id, unique_id, timestamp, pmtwofive, pmten):
    data = {
      'sensorID' : id,
      'uniqueID' : unique_id,
      'timecollected' : timestamp,
      'pmtwofive' : pmtwofive,
      'pmten': pmten
    }

    json_str = json.dumps(data)
    return json_str

def sensor_wake(ser):
    bytes = [b'\xaa', #head
    b'\xb4', #command 1
    b'\x06', #data byte 1
    b'\x01', #data byte 2 (set mode)
    b'\x01', #data byte 3 (sleep)
    b'\x00', #data byte 4
    b'\x00', #data byte 5
    b'\x00', #data byte 6
    b'\x00', #data byte 7
    b'\x00', #data byte 8
    b'\x00', #data byte 9
    b'\x00', #data byte 10
    b'\x00', #data byte 11
    b'\x00', #data byte 12
    b'\x00', #data byte 13
    b'\xff', #data byte 14 (device id byte 1)
    b'\xff', #data byte 15 (device id byte 2)
    b'\x06', #checksum
    b'\xab'] #tail
    
    for b in bytes:
        ser.write(b)
        
        
def sensor_sleep(ser):
    bytes = [b'\xaa', #head
    b'\xb4', #command 1
    b'\x06', #data byte 1
    b'\x01', #data byte 2 (set mode)
    b'\x00', #data byte 3 (sleep)
    b'\x00', #data byte 4
    b'\x00', #data byte 5
    b'\x00', #data byte 6
    b'\x00', #data byte 7
    b'\x00', #data byte 8
    b'\x00', #data byte 9
    b'\x00', #data byte 10
    b'\x00', #data byte 11
    b'\x00', #data byte 12
    b'\x00', #data byte 13
    b'\xff', #data byte 14 (device id byte 1)
    b'\xff', #data byte 15 (device id byte 2)
    b'\x05', #checksum
    b'\xab'] #tail
    
    for b in bytes:
        ser.write(b)
         
def sleep_and_count(seconds):
    for i in range(seconds,0,-1):
        remaining_seconds = i % 60
        remaining_minutes = (i - remaining_seconds) / 60
        print('Waiting for %d minutes and %d seconds ...' % (remaining_minutes, remaining_seconds), end='\r')
        time.sleep(1)
    print()

		
def main():
    args = parse_command_line_args()
    project_id = args.project_id
    gcp_location = args.cloud_region
    registry_id = args.registry_id
    device_id = args.device_id
    interval = args.interval
    ssl_private_key_filepath = args.private_key_file
    ssl_algorithm = args.algorithm
    root_cert_filepath = args.ca_certs
    sensorID = registry_id + "." + device_id
    googleMQTTURL = args.mqtt_bridge_hostname
    googleMQTTPort = args.mqtt_bridge_port
    
    _CLIENT_ID = 'projects/{}/locations/{}/registries/{}/devices/{}'.format(project_id, gcp_location, registry_id, device_id)
    _MQTT_TOPIC = '/devices/{}/events'.format(device_id)

    ser = serial.Serial('/dev/ttyUSB0') # initialize receiver USB
    print("Ready. Waiting for signal.")
    

    client = mqtt.Client(client_id=_CLIENT_ID)
    cur_time = datetime.datetime.utcnow()
    # authorization is handled purely with JWT, no user/pass, so username can be whatever
    client.username_pw_set(
        username='unused',
        password=create_jwt(cur_time, project_id, ssl_private_key_filepath, ssl_algorithm))

    client.on_connect = on_connect
    client.on_publish = on_publish

    client.tls_set(ca_certs=root_cert_filepath) # Replace this with 3rd party cert if that was used when creating registry
    client.connect(googleMQTTURL, googleMQTTPort)

    jwt_refresh = time.time() + ((token_life - 1) * 60) #set a refresh time for one minute before the JWT expires

    client.loop_start()

    try:
        sensor_wake(ser)
        print("Sensor enabled.")
        sleep_and_count(30)
        data = []
        for index in range(0,10):
          datum = ser.read()
          data.append(datum)
        pmtwofive = int.from_bytes(b''.join(data[2:4]), byteorder='little') / 10
        pmten = int.from_bytes(b''.join(data[4:6]), byteorder='little') / 10
        currentTime = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        uniqueID = str(uuid.uuid4()) + "-" + sensorID
        payload = createJSON(sensorID, uniqueID, currentTime, pmtwofive, pmten)
        client.publish(_MQTT_TOPIC, payload, qos=1)
        print("{}\n".format(payload))
        sensor_sleep(ser)
      except Exception as e:
        print("There was an error")
        print (e)
                       			
      client.loop_stop()

if __name__ == '__main__':
	main()
