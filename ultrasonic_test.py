import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

TRIG = 24
ECHO = 25

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

while True:

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    while GPIO.input(ECHO)==0:
        start = time.time()

    while GPIO.input(ECHO)==1:
        stop = time.time()

    distance = (stop-start)*17150

    print("Distance:", round(distance,2),"cm")

    time.sleep(1)