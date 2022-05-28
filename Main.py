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
from adafruit_servokit import ServoKit

#os.system('modprobe w1-gpio')
#os.system('modprobe w1-therm')
#base_dir = '/sys/bus/w1/devices/'
#device_folder = glob.glob(base_dir + '28*')[0]
#device_file = device_folder + '/w1_slave'

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
urlTimeout = 5
isConnected = False
while isConnected == False:
    try:
        request = requests.get(url, timeout=urlTimeout)
        isConnected = True
    except (requests.ConnectionError, requests.Timeout) as exception:
        print("No internet connection.")


#MainLedPin = 25
#MainFan = 15
SENSOR = Adafruit_DHT.AM2302

transistor = 14

#livingRoomSensorPin = 4
#livingRoomRelayFanPin = 1
#livingRoomRelayLightPin = 14
#livingRoomKey = 18
#livingRoomStr = "Гостиная"


GuestBathSensorPin = 4
GuestBathRelayLightPin = 22
GuestBathRelayFanPin = 27
GuestBathKey = 23
GuestBathStr = "Гостевой туалет"

BalconSensorPin = 24
BalconStr = "Мезонин"

#GPIO.setup(livingRoomKey, GPIO.IN)
#GPIO.setup(livingRoomRelayFanPin, GPIO.OUT)
#GPIO.output(livingRoomRelayFanPin, GPIO.LOW)
#GPIO.setup(livingRoomRelayLightPin, GPIO.OUT)
#GPIO.output(livingRoomRelayLightPin, GPIO.LOW)

GPIO.setup(GuestBathKey, GPIO.IN)
GPIO.setup(GuestBathRelayFanPin, GPIO.OUT)
GPIO.output(GuestBathRelayFanPin, GPIO.LOW)
GPIO.setup(GuestBathRelayLightPin, GPIO.OUT)
GPIO.output(GuestBathRelayLightPin, GPIO.LOW)




#GPIO.setup(MainLedPin, GPIO.OUT)
#GPIO.output(MainLedPin, GPIO.LOW)
#GPIO.setup(MainFan, GPIO.OUT)
#GPIO.output(MainFan, GPIO.LOW)
GPIO.setup(transistor, GPIO.OUT)
GPIO.output(transistor, GPIO.HIGH)

array = [[GuestBathStr, False], [BalconStr, False]]
kit = ServoKit(channels=16)
kit.servo[1].angle = 180


firebase = pyrebase.initialize_app(config)
db = firebase.database()



def convertValue(value):
    return str("{0:0.2f}".format(value))

#Отправка в Firebase температуры внутри распредКоробки
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
       # GPIO.output(MainLedPin, GPIO.HIGH)
       # time.sleep(3)
       # GPIO.output(MainLedPin, GPIO.LOW)
        time.sleep(5*60)


def SendStatusErrorHandler():
    counter = 0
    while True:
        date = str(datetime.datetime.now())
        try:
            request = requests.get(url, timeout=urlTimeout)
            db.child("home").child("Status").set("Maybe online = " + str(counter))
            counter+=1
        except:
            f = open("home/pi/Documents/ErrorLog.txt", "a")
            f.write("FUUUUCKKK, but great: date = "+ date+"\n")
            f.close()
            os.system("shutdown -r now")
        time.sleep(60)

#Включение главного канального вентилятора
def MainFanWork():
    while True:
        isWork = False
        for i in range(0,2):
            if array[i][1] == True:
                isWork = True
                break
        GPIO.output(MainFan, isWork)
        db.child("home").child("IsMainFanWork").set(isWork)
        time.sleep(1*60)

#Oтправка в БД показания данных с датчиков
def sendDataToDatabase(sensorPin: int, roomStr:str):
    while True:
        isConnected = False
        while isConnected == False:
            try:
                request = requests.get(url, timeout=urlTimeout)
                isConnected = True
                conn = psycopg2.connect(dbname='d8uq0o35eq55kl', user='zftenjusikiyjk',
                        password='7369c86979b2cbf92b10879ec08ba1ca99394ea761c0462a4baf24d3a2225685', host='ec2-176-34-168-83.eu-west-1.compute.amazonaws.com')
                humidity, temperature = Adafruit_DHT.read_retry(SENSOR, sensorPin)
                date = str(datetime.datetime.now())
                print("\nsendDataToDatabase - - sensor = " + str(sensorPin) + " humidity = " + str(humidity))
                if humidity is not None and temperature is not None:
                    cursor = conn.cursor()
                    with conn.cursor() as cursor:
                        conn.autocommit = True
                        values = [
                        (date, convertValue(temperature), convertValue(humidity), sensorPin)
                    ]
                        insert = sql.SQL('INSERT INTO home (date, temperature, humidity, sensor) VALUES {}').format(
                      sql.SQL(',').join(map(sql.Literal, values))
                    )
                        cursor.execute(insert)
                        conn.close()
                db.child("home").child("rooms").child(roomStr).child("status").set(str(date) + " humidity = " + str(humidity) + " temp = " + str(temperature))
            except (requests.ConnectionError, requests.Timeout) as exception:
                print("No internet connection.")
        time.sleep(5*60)


#Turn on off vent depend on the sensor
def sensorFanWork(sensorPin: int, relayPinFan:int, roomStr:str):
    previous = 50
    timeout = 60
    countTimesWork = 0
    while True:
        #GPIO.output(relayPinFan, False)
        db.child("home").child("rooms").child(roomStr).child("isFanWork").set(False)
        humidity, temperature = Adafruit_DHT.read_retry(SENSOR, sensorPin)
        date = str(datetime.datetime.now())
        print("\nsensor = " + roomStr + " humidity = " + str(humidity))
        if humidity is not None and temperature is not None:

               # Check and write data to Firebase datebase
            isFanWorkRoot = db.child("home").child("rooms").child(roomStr).child("isFanWorkRoot").get().val()
            whenTurnOnFan = db.child("home").child("rooms").child(roomStr).child("whenTurnOnFan").get().val()

            isIWork = False
            if humidity > whenTurnOnFan:
                isIWork = True
                if countTimesWork > 2:
                    isIWork = False
                    countTimesWork = 0
                else:
                    countTimesWork+=1
            else:
                isIWork = False

            if isFanWorkRoot == True:
                isIWork = False
                # Turn on/off the relay
            GPIO.output(relayPinFan, isIWork)
            db.child("home").child("rooms").child(roomStr).child("isFanWork").set(isIWork)

            index = 0
            for i in range(0, 2):
                try:
                    index = array[i].index(roomStr)
                    array[index][1] = isIWork
                    break
                except:
                    continue

            # define timeout
            if abs(humidity - previous) > 5:
                timeout = 1*60
            else:
                if abs(humidity - previous) > 2:
                    timeout = 2*60
                if abs(humidity - previous) < 0.4:
                    timeout = 5*60
                else:
                    timeout = 3*60
            previous = humidity
        else:
            GPIO.output(relayPinFan, False)
            timeout = 10
            db.child("home").child("rooms").child(roomStr).child("isFanWork").set(False)
            GPIO.output(transistor, GPIO.LOW)
            time.sleep(10)
            GPIO.output(transistor, GPIO.HIGH)
        time.sleep(timeout)



#Open Close servo depend on the sensor
def sensorServoWork(sensorPin: int, servoPin:int, roomStr:str):
    previous = 50
    prevOpenServo = False
    timeout = 60
    countTimesWork = 0
    while True:
        humidity, temperature = Adafruit_DHT.read_retry(SENSOR, sensorPin)
        date = str(datetime.datetime.now())
        print("\nSERVO sensor = " + roomStr + " humidity = " + str(humidity))
        if humidity is not None and temperature is not None:
               # Check and write data to Firebase datebase
            isServoOpenRoot = db.child("home").child("rooms").child(roomStr).child("isFanWorkRoot").get().val()
            whenOpenServo = db.child("home").child("rooms").child(roomStr).child("whenTurnOnFan").get().val()

            isIWork = False
            if humidity > whenOpenServo:
                isIWork = True
            if isServoOpenRoot == True:
                isIWork = True
                
                # Turn on/off the servo
            if (isIWork == False and prevOpenServo == True):
                for i in range (65, 180):
                    kit.servo[servoPin].angle = i
                    time.sleep(0.01)
            if (isIWork == True and prevOpenServo == False):
                for i in range (180, 65, -1):
                    kit.servo[servoPin].angle = i
                    time.sleep(0.01)

            prevOpenServo = isIWork
            db.child("home").child("rooms").child(roomStr).child("isFanWork").set(isIWork)

            index = 0
            for i in range(0, 2):
                try:
                    index = array[i].index(roomStr)
                    array[index][1] = isIWork
                    break
                except:
                    continue

            # define timeout
            if abs(humidity - previous) > 5:
                timeout = 1*60
            else:
                if abs(humidity - previous) > 2:
                    timeout = 2*60
                if abs(humidity - previous) < 0.4:
                    timeout = 5*60
                else:
                    timeout = 3*60
            previous = humidity
        else:
            timeout = 10
            GPIO.output(transistor, GPIO.LOW)
            time.sleep(10)
            GPIO.output(transistor, GPIO.HIGH)
        time.sleep(timeout)        


#включение света и вентиляции по нажатию кнопки
def FanLightRelayWork(relayPinFan:int, relayPinLight:int, key:int, roomStr:str):
    isTurnOn = False
    timer = 0
    while True:
        if GPIO.input(key) == False:
            if isTurnOn == False:
                GPIO.output(relayPinLight, GPIO.HIGH)
                time.sleep(1)
                isTurnOn = True
                timer = 0
            else:
                GPIO.output(relayPinLight, GPIO.LOW)
                GPIO.output(relayPinFan, GPIO.HIGH)
                isTurnOn = False
                db.child("home").child("rooms").child(roomStr).child("isFanWork").set(True)
                index = 0
                for i in range(0, 2):
                    try:
                        index = array[i].index(roomStr)
                        array[index][1] = True
                        break
                    except:
                        continue
            #GPIO.output(MainLedPin, GPIO.HIGH)
            time.sleep(1)
            #GPIO.output(MainLedPin, GPIO.LOW)
            timer = -5*600
            db.child("home").child("rooms").child(roomStr).child("isLightOn").set(isTurnOn)
        timer += 1
        if timer > 5*600:
            GPIO.output(relayPinLight, GPIO.LOW)
            isTurnOn = False
            db.child("home").child("rooms").child(roomStr).child("isLightOn").set(isTurnOn)
            timer = -5*600
        time.sleep(0.2)

#Включение по нажатию кнопки только света
def KeyLightRelayWork(relayPinLight:int, key:int, roomStr:str):
    isTurnOn = False
    while True:
        if GPIO.input(key) == False:
            time.sleep(0.2)
            if isTurnOn == False:
                GPIO.output(relayPinLight, GPIO.HIGH)
                isTurnOn = True

            else:
                GPIO.output(relayPinLight, GPIO.LOW)
                isTurnOn = False
            #GPIO.output(MainLedPin, GPIO.HIGH)
            #time.sleep(1)
            #GPIO.output(MainLedPin, GPIO.LOW)
            db.child("home").child("rooms").child(roomStr).child("isLightOn").set(isTurnOn)
        time.sleep(0.1)

#Включение света по состоянию Firebase
def LightRelayWork(relayPinLight:int, key:int, roomStr:str):
    isTurnOn = False
    while True:
        isLightOn = db.child("home").child("rooms").child(roomStr).child("isLightOn").get().val()
        if isLightOn == True and isTurnOn == False:
            isTurnOn = True
            GPIO.output(relayPinLight, GPIO.HIGH)
            db.child("home").child("rooms").child(roomStr).child("isLightOn").set(isTurnOn)
            #GPIO.output(MainLedPin, GPIO.HIGH)
            #time.sleep(1)
            #GPIO.output(MainLedPin, GPIO.LOW)

        if isLightOn == False and  isTurnOn == True:
            GPIO.output(relayPinLight, GPIO.LOW)
            isTurnOn = False
            db.child("home").child("rooms").child(roomStr).child("isLightOn").set(isTurnOn)
            #GPIO.output(MainLedPin, GPIO.HIGH)
            #time.sleep(1)
            #GPIO.output(MainLedPin, GPIO.LOW)
        time.sleep(3)



ErrorHandler = threading.Thread(target=SendStatusErrorHandler)
#SendDataToDB = threading.Thread(target=sendDataToDatabase)
FanMainWork = threading.Thread(target=MainFanWork)
#tempInside = threading.Thread(target=GetTempInside)   sendDataToDatabase

one = threading.Thread(target=sensorFanWork, args=(GuestBathSensorPin, GuestBathRelayFanPin, GuestBathStr))
oneFanLight = threading.Thread(target=FanLightRelayWork, args=(GuestBathRelayFanPin, GuestBathRelayLightPin, GuestBathKey, GuestBathStr))
oneLight = threading.Thread(target=LightRelayWork, args=(GuestBathRelayLightPin, GuestBathKey, GuestBathStr))
one_sendSensorData = threading.Thread(target=sendDataToDatabase, args=(GuestBathSensorPin, GuestBathStr))
twoServo = threading.Thread(target=sensorServoWork, args=(GuestBathSensorPin, 1, BalconStr))

two_sendSensorData = threading.Thread(target=sendDataToDatabase, args=(BalconSensorPin, BalconStr))



if __name__ == '__main__':
    conn = psycopg2.connect(dbname='d8uq0o35eq55kl', user='zftenjusikiyjk',
                        password='7369c86979b2cbf92b10879ec08ba1ca99394ea761c0462a4baf24d3a2225685', host='ec2-176-34-168-83.eu-west-1.compute.amazonaws.com')
    with conn.cursor() as cursor:
        conn.autocommit = True
        insert = sql.SQL("DELETE FROM home WHERE date < CURRENT_TIMESTAMP - INTERVAL '3day'")
        cursor.execute(insert)

    one.start()
    oneFanLight.start()
    oneLight.start()
    one_sendSensorData.start()
    twoServo.start()
    #two_sendSensorData.start()

    #SendDataToDB.start()
    ErrorHandler.start()
    #tempInside.start()
    #FanMainWork.start()
    time.sleep(4199999)
