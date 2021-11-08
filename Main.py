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
livingRoomRelayPin = 4
livingRoomStr = "Гостиная"

GPIO.setup(livingRoomRelayPin, GPIO.OUT)
GPIO.output(livingRoomRelayPin, GPIO.LOW)

firebase = pyrebase.initialize_app(config)
db = firebase.database()

conn = psycopg2.connect(dbname='d8uq0o35eq55kl', user='zftenjusikiyjk',
                        password='7369c86979b2cbf92b10879ec08ba1ca99394ea761c0462a4baf24d3a2225685', host='ec2-176-34-168-83.eu-west-1.compute.amazonaws.com')
cursor = conn.cursor()


def convertTemp(value):
    return str("{0:0.1f}".format(value))

def convertHum(value):
    return str("{0:0.2f}".format(value))


def sensorWork(sensorPin: int, relayPin:int, roomStr:str):
    previous = 50
    try:
        while True:
            humidity, temperature = Adafruit_DHT.read_retry(SENSOR, sensorPin)
            date = str(datetime.datetime.now())
            if humidity is not None and temperature is not None:
                # Write data to SQL Database
                with conn.cursor() as cursor:
                    conn.autocommit = True
                    values = [
                        (date, convertTemp(temperature), convertHum(humidity), sensorPin)
                    ]
                    insert = sql.SQL('INSERT INTO home (date, temperature, humidity, sensor) VALUES {}').format(
                        sql.SQL(',').join(map(sql.Literal, values))
                    )
                    cursor.execute(insert)
                # Check and write data to Firebase datebase and turn on/off the relay 
                isFanWorkRoot = db.child("home").child("rooms").child(roomStr).child("isFanWorkRoot").get().val()
                if humidity > 54 or isFanWorkRoot:
                    GPIO.output(relayPin, GPIO.HIGH)
                    db.child("home").child("rooms").child("Гостиная").child("isFanWork").set(True)
                else:
                    GPIO.output(relayPin, GPIO.LOW)
                    db.child("home").child("rooms").child("Гостиная").child("isFanWork").set(False)


            # define timeout
            if abs(humidity - previous) > 5:
                timeout = 60
            else:
                if abs(humidity - previous) > 2:
                    timeout = 150
                if abs(humidity - previous) < 0.4:
                    timeout = 15*60
                else:
                    timeout = 360
            previous = humidity
            time.sleep(timeout)
    except KeyboardInterrupt:
        GPIO.cleanup()



sensorWork(livingRoomSensorPin, livingRoomRelayPin, livingRoomStr)


with conn.cursor() as cursor:
    conn.autocommit = True
    insert = sql.SQL("DELETE FROM home WHERE date < CURRENT_TIMESTAMP - INTERVAL '2day'")
    cursor.execute(insert)



