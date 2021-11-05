import Adafruit_DHT
import RPi.GPIO as GPIO
import time
import datetime

SENSOR = Adafruit_DHT.AM2302
PIN = 22
LED = 23
SOUND = 25
LED2 = 27

GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED2, GPIO.OUT)
GPIO.output(LED2, GPIO.LOW)
GPIO.setup(LED, GPIO.OUT)
GPIO.output(LED, GPIO.LOW)
GPIO.setup(SOUND, GPIO.OUT)
GPIO.output(SOUND, GPIO.LOW)

try:
    while True:
        humidity, temperature = Adafruit_DHT.read_retry(SENSOR, PIN)
        f = open("/home/pi/Documents/logTempHum.txt", "a")
        date = str(datetime.datetime.now())
        if humidity is not None and temperature is not None:
            f.write(date + ":    Temp={0:0.1f}C   Humidity={1:0.1f}%\n".format(temperature, humidity))
            print(date + ":     Temp={0:0.1f}*C  Humidity={1:0.1f}%".format(temperature, humidity))

            if humidity > 75:
                while humidity > 75:
                    GPIO.output(LED2, GPIO.HIGH)
                    time.sleep(0.3)
                    GPIO.output(LED2, GPIO.LOW)
                    time.sleep(0.3)
                    GPIO.output(LED, GPIO.HIGH)
                    time.sleep(0.3)
                    GPIO.output(LED, GPIO.LOW)
                    humidity, temerature = Adafruit_DHT.read_retry(SENSOR, PIN)
            if humidity > 62:
                # f.write(date + ":    Temp={0:0.1f}*C  Humidity={1:0.1f}%\n".format(temperature, humidity))
                GPIO.output(LED2, GPIO.HIGH)
                GPIO.output(LED, GPIO.HIGH)
            else:
                if humidity > 45:
                    GPIO.output(LED2, GPIO.LOW)
                    GPIO.output(LED, GPIO.HIGH)
                else:
                    GPIO.output(LED, False)
                    GPIO.output(LED2, False)
                    pwm = GPIO.PWM(LED, 100)
                    pwm.start(10)

                while humidity <= 45:
                    for i in range(0, 101):
                        pwm.ChangeDutyCycle(i)
                        time.sleep(0.3)
                    time.sleep(5)
                    for i in range(100, -1, -1):
                        pwm.ChangeDutyCycle(i)
                        time.sleep(0.3)
                    time.sleep(3)
                humidity, temperature = Adafruit_DHT.read_retry(SENSOR, PIN)
                pwm.stop()
        else:
            f.write(date + ":    Failed to retrieve data from humidity sensor\n")
    f.close()
    time.sleep(300)
except KeyboardInterrupt:
    GPIO.cleanup()
