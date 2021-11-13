import Adafruit_DHT
import RPi.GPIO as GPIO
import time
import datetime
import sys
sys.path.append('/home/pi/.local/lib/python3.7/site-packages')
import psycopg2
from psycopg2 import sql
import requests as requests
import pyrebase
import threading
import os
import glob

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
config = {
  "apiKey": "AIzaSyAsCdYa-pxBbbrpzS9U9ck7sot8JYflPOQ",
  "authDomain": "smart-house-e324f.firebaseapp.com",
  "databaseURL": "https://smart-house-e324f-default-rtdb.firebaseio.com",
  "projectId": "smart-house-e324f",
  "storageBucket": "smart-house-e324f.appspot.com",
  "messagingSenderId": "775955075453",
  "appId": "1:775955075453:web:92e399f42f22f0c1effc14",
  "measurementId": "G-4DPWQF734S"
}

url = "http://www.google.com"
timeout = 5
isConnected = False
while isConnected == False:
    try:
        request = requests.get(url, timeout=timeout)
        isConnected = True
    except (requests.ConnectionError, requests.Timeout) as exception:
        print("No internet connection.")



SENSOR = Adafruit_DHT.AM2302
livingRoomSensorPin = 22
livingRoomRelayFanPin = 4
livingRoomStr = "Гостиная"

GuestBathSensorPin = 22
GuestBathRelayLightPin = 23
GuestBathRelayFanPin = 24
GuestBathKey = 27
GuestBathStr = "Гостевая ванная"

GPIO.setup(livingRoomRelayFanPin, GPIO.OUT)
GPIO.output(livingRoomRelayFanPin, GPIO.LOW)


GPIO.setup(GuestBathRelayLightPin, GPIO.OUT)
GPIO.output(GuestBathRelayLightPin, GPIO.LOW)
GPIO.setup(GuestBathRelayFanPin, GPIO.OUT)
GPIO.output(GuestBathRelayFanPin, GPIO.LOW)
GPIO.setup(GuestBathKey, GPIO.IN)


firebase = pyrebase.initialize_app(config)
db = firebase.database()
conn = psycopg2.connect(dbname='d8uq0o35eq55kl', user='zftenjusikiyjk',
                        password='7369c86979b2cbf92b10879ec08ba1ca99394ea761c0462a4baf24d3a2225685', host='ec2-176-34-168-83.eu-west-1.compute.amazonaws.com')


def convertTemp(value):
    return str("{0:0.1f}".format(value))

def convertHum(value):
    return str("{0:0.2f}".format(value))

def GetTempInside():
    while True:
        f = open(device_file, 'r')
        lines = f.readlines()
        f.close()
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = read_temp_raw()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp = float(temp_string) / 1000.0
            db.child("home").child("TempInsideBox").set(temp)
        time.sleep(5*60)   

def sensorWork(sensorPin: int, relayPinFan:int, roomStr:str):
    previous = 50
    try:
        while True:
            humidity, temperature = Adafruit_DHT.read_retry(SENSOR, sensorPin)
            date = str(datetime.datetime.now())
            if humidity is not None and temperature is not None:
                # Write data to SQL Database
                cursor = conn.cursor()
                with conn.cursor() as cursor:
                    conn.autocommit = True
                    values = [
                        (date, convertTemp(temperature), convertHum(humidity), sensorPin)
                    ]
                    insert = sql.SQL('INSERT INTO home (date, temperature, humidity, sensor) VALUES {}').format(
                        sql.SQL(',').join(map(sql.Literal, values))
                    )
                    cursor.execute(insert)
                    #cursor.close()
                # Check and write data to Firebase datebase and turn on/off the relay 
                isFanWorkRoot = db.child("home").child("rooms").child(roomStr).child("isFanWorkRoot").get().val()
                whenTurnOnFan = db.child("home").child("rooms").child(roomStr).child("whenTurnOnFan").get().val()
                if humidity > whenTurnOnFan or isFanWorkRoot:
                    GPIO.output(relayPinFan, GPIO.HIGH)
                    db.child("home").child("rooms").child(roomStr).child("isFanWork").set(True)
                else:
                    GPIO.output(relayPinFan, GPIO.LOW)
                    db.child("home").child("rooms").child(roomStr).child("isFanWork").set(False)


            # define timeout
            if abs(humidity - previous) > 5:
                timeout = 60
            else:
                if abs(humidity - previous) > 2:
                    timeout = 3*60
                if abs(humidity - previous) < 0.4:
                    timeout = 10*60
                else:
                    timeout = 5*60
            previous = humidity
            time.sleep(timeout)
    except KeyboardInterrupt:
        GPIO.cleanup()


def FanLightRelayWork(relayPinFan:int, relayPinLight:int, key:int, roomStr:str):
    isTurnOn = False
    while True:
        if GPIO.input(key) == False:
            time.sleep(0.2)
            if isTurnOn == False:
                GPIO.output(relayPinFan, GPIO.HIGH)
                GPIO.output(relayPinLight, GPIO.HIGH)
                db.child("home").child("rooms").child(roomStr).child("isFanWork").set(True)
                isTurnOn = True
                
            else:
                GPIO.output(relayPinLight, GPIO.LOW)
                isTurnOn = False
            db.child("home").child("rooms").child(roomStr).child("isLightOn").set(isTurnOn)
        time.sleep(0.2)

def LightRelayWork(relayPinLight:int, key:int, roomStr:str):
    isTurnOn = False
    while True:
        isLightOn = db.child("home").child("rooms").child(roomStr).child("isLightOn").get().val()
        if isLightOn == True and isTurnOn == False:
            isTurnOn = True
            GPIO.output(relayPinLight, GPIO.HIGH)
            db.child("home").child("rooms").child(roomStr).child("isLightOn").set(isTurnOn)
            
        if isLightOn == False and  isTurnOn == True:
            GPIO.output(relayPinLight, GPIO.LOW)
            isTurnOn = False
            db.child("home").child("rooms").child(roomStr).child("isLightOn").set(isTurnOn)
        time.sleep(15)     

one = threading.Thread(target=sensorWork, args=(GuestBathSensorPin, GuestBathRelayFanPin, GuestBathStr))
oneFanLight = threading.Thread(target=FanLightRelayWork, args=(GuestBathRelayFanPin, GuestBathRelayLightPin, GuestBathKey, GuestBathStr))
oneLight = threading.Thread(target=LightRelayWork, args=(GuestBathRelayLightPin, GuestBathKey, GuestBathStr))
tempInside = threading.Thread(target=GetTempInside)
#two = threading.Thread(target=sensorWork, args=(livingRoomSensorPin, livingRoomRelayFanPin, livingRoomStr))

if __name__ == '__main__':
    one.start()
    oneFanLight.start()
    oneLight.start()
    tempInside.start()
    time.sleep(4199999)


with conn.cursor() as cursor:
    conn.autocommit = True
    insert = sql.SQL("DELETE FROM home WHERE date < CURRENT_TIMESTAMP - INTERVAL '2day'")
    cursor.execute(insert)
