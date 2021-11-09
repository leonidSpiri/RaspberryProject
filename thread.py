import time
import threading


def test(text: str):
    while True:
        print(text)
        print()
        time.sleep(1)


one = threading.Thread(target=test, args="1")
two = threading.Thread(target=test, args="2")

if __name__ == '__main__':
    one.start()
    two.start()
