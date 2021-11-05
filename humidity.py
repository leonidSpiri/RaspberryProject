import Adafruit_DHT
import RPi.GPIO as GPIO
import time
import datetime
import psycopg2
from psycopg2 import sql

conn = psycopg2.connect(dbname='d8uq0o35eq55kl', user='zftenjusikiyjk',
                        password='7369c86979b2cbf92b10879ec08ba1ca99394ea761c0462a4baf24d3a2225685',
                        host='ec2-176-34-168-83.eu-west-1.compute.amazonaws.com')
cursor = conn.cursor()
SENSOR = Adafruit_DHT.AM2302
GPIO.cleanup()
mainPin = 22


def convertTemp(value):
    return str("{0:0.1f}".format(value))


def convertHum(value):
    return str("{0:0.1f}".format(value))


def sensorWork(pin: int):
    previous = 45

    try:
        while True:
            humidity, temperature = Adafruit_DHT.read_retry(SENSOR, pin)
            date = str(datetime.datetime.now())
            print(date + ":     Temp={0:0.1f}*C  Humidity={1:0.1f}%".format(temperature, humidity))
            if humidity is not None and temperature is not None:
                with conn.cursor() as cursor:
                    conn.autocommit = True
                    values = [
                        (date, convertTemp(temperature), convertHum(humidity))
                    ]
                    insert = sql.SQL('INSERT INTO home (date, temperature, humidity) VALUES {}').format(
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
            time.sleep(timeout)
            previous = humidity
    except KeyboardInterrupt:
        GPIO.cleanup()


with conn.cursor() as cursor:
    conn.autocommit = True
    insert = sql.SQL("DELETE FROM home WHERE date < CURRENT_TIMESTAMP - INTERVAL '2day'")
    cursor.execute(insert)

sensorWork(mainPin)
