import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

IN1 = 17
IN2 = 18
IN3 = 22
IN4 = 23

pins = [IN1, IN2, IN3, IN4]

for pin in pins:
    GPIO.setup(pin, GPIO.OUT)

def forward():
    GPIO.output(IN1,1)
    GPIO.output(IN2,0)

    GPIO.output(IN3,1)
    GPIO.output(IN4,0)

def backward():
    GPIO.output(IN1,0)
    GPIO.output(IN2,1)

    GPIO.output(IN3,0)
    GPIO.output(IN4,1)

def left():
    GPIO.output(IN1,0)
    GPIO.output(IN2,1)

    GPIO.output(IN3,1)
    GPIO.output(IN4,0)

def right():
    GPIO.output(IN1,1)
    GPIO.output(IN2,0)

    GPIO.output(IN3,0)
    GPIO.output(IN4,1)

def stop():
    for pin in pins:
        GPIO.output(pin,0)

forward()
# backward()
# left()
# right()

time.sleep(2)

stop()

GPIO.cleanup()
