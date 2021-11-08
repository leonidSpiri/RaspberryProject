import Adafruit_DHT
import RPi.GPIO as GPIO
import time
import datetime
import sys
sys.path.append('/home/pi/.local/lib/python3.7/site-packages')
import psycopg2
from psycopg2 import sql
import requests as requests

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
livingRoomPin = 22
#GPIO.cleanup()
conn = psycopg2.connect(dbname='d8uq0o35eq55kl', user='zftenjusikiyjk',
                        password='7369c86979b2cbf92b10879ec08ba1ca99394ea761c0462a4baf24d3a2225685', host='ec2-176-34-168-83.eu-west-1.compute.amazonaws.com')
cursor = conn.cursor()


def convertTemp(value):
    return str("{0:0.1f}".format(value))

def convertHum(value):
    return str("{0:0.2f}".format(value))


def sensorWork(pin: int):
    previous = 50
    try:
        while True:
            humidity, temperature = Adafruit_DHT.read_retry(SENSOR, pin)
            date = str(datetime.datetime.now())
            if humidity is not None and temperature is not None:
                with conn.cursor() as cursor:
                    conn.autocommit = True
                    values = [
                        (date, convertTemp(temperature), convertHum(humidity), pin)
                    ]
                    insert = sql.SQL('INSERT INTO home (date, temperature, humidity, sensor) VALUES {}').format(
                        sql.SQL(',').join(map(sql.Literal, values))
                    )
                    cursor.execute(insert)

            if abs(humidity - previous) > 5:
                timeout = 60
            else:
                if abs(humidity - previous) > 2:
                    timeout = 150
                else:
                    timeout = 360
            previous = humidity
            time.sleep(timeout)
    except KeyboardInterrupt:
        GPIO.cleanup()



sensorWork(livingRoomPin)


with conn.cursor() as cursor:
    conn.autocommit = True
    insert = sql.SQL("DELETE FROM home WHERE date < CURRENT_TIMESTAMP - INTERVAL '2day'")
    cursor.execute(insert)
