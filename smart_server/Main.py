import requests
import time
import RPi.GPIO as GPIO
import glob
import threading

base_url = "http://192.168.1.122:9888/api/"
base_dir = '/sys/bus/w1/devices/'
fan_pin = 21
cond_pin = 20
motion_pin = 25
room_temp_pin = 4
box_temp_pin = 5


def retrieve_data_from_server():
    try:
        url = base_url + "mobile/last_request"
        response = requests.get(url)
        if response.ok:
            requirements_list = response.text.split(", ")
            for requirement in requirements_list:
                pair = requirement.split(":")
                is_turn_on = True if pair[1] == "true" else False
                GPIO.output(int(pair[0]), is_turn_on)
                print("gpio = " + pair[0] + " = " + str(is_turn_on))
    except:
        time.sleep(60)


def read_temp_raw(device_file: str):
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines


def read_temp(device_file: str):
    lines = read_temp_raw(device_file)
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw(device_file)
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        temp_c = int(float(temp_string) / 1000.0)
        return temp_c


def read_motion():
    if GPIO.input(motion_pin):
        return True
    return False


def send_data_to_server():
    try:
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '/w1_slave'
        box_temp = read_temp(device_file)
        device_folder = glob.glob(base_dir + '28*')[1]
        device_file = device_folder + '/w1_slave'
        room_temp = read_temp(device_file)
        url = base_url + "rasp_state"
        is_fan_work = True if GPIO.input(fan_pin) == 1 else False
        is_cond_work = True if GPIO.input(cond_pin) == 1 else False
        payload = {
            "newRequiredState": f"21:{is_fan_work},20:{is_cond_work},4:{room_temp},5:{box_temp}",
            "isSecurityViolated": read_motion()
        }
        post_response = requests.post(url, json=payload)
        post_response_json = post_response.json()
        print(post_response_json)
    except:
        time.sleep(60)


def main():
    print("Main")
    while True:
        retrieve_data_from_server()
        time.sleep(10)
        send_data_to_server()
        time.sleep(60)


def security():
    print("Security")
    while True:
        retrieve_data_from_server()
        if read_motion():
            url = base_url + "security/violated"
            requests.post(url)
            time.sleep(30)
        else:
            time.sleep(10)


mainWork = threading.Thread(target=main)
securityWork = threading.Thread(target=security)

if __name__ == '__main__':
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(fan_pin, GPIO.OUT)
    GPIO.output(fan_pin, GPIO.LOW)
    GPIO.setup(cond_pin, GPIO.OUT)
    GPIO.output(cond_pin, GPIO.LOW)
    GPIO.setup(motion_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    mainWork.start()
    securityWork.start()
