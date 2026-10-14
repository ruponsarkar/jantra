from flask import Flask, render_template, Response, jsonify
from picamera2 import Picamera2
# from gpiozero import AngularServo
import RPi.GPIO as GPIO
import cv2
import threading
import time

app = Flask(__name__)

# =========================
# GLOBAL STATUS
# =========================

robot_status = "Ready"

# =========================
# GPIO SETUP
# =========================

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

IN1 = 17
IN2 = 18
IN3 = 22
IN4 = 23

TRIG = 24
ECHO = 25

for pin in [IN1, IN2, IN3, IN4]:
    GPIO.setup(pin, GPIO.OUT)

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# =========================
# SERVO
# =========================

# servo = AngularServo(
#     12,
#     min_angle=-90,
#     max_angle=90
# )

# camera_angle = 0

# =========================
# CAMERA
# =========================

picam2 = Picamera2()

picam2.configure(
    picam2.create_video_configuration(
        main={"size": (640, 480)}
    )
)

picam2.start()

# =========================
# GLOBAL STATE
# =========================

current_direction = "stop"
state_lock = threading.Lock()

# =========================
# MOTOR FUNCTIONS
# =========================

def stop():

    global current_direction
    global robot_status

    GPIO.output(IN1, 0)
    GPIO.output(IN2, 0)
    GPIO.output(IN3, 0)
    GPIO.output(IN4, 0)

    with state_lock:
        current_direction = "stop"

    robot_status = "Stopped"

    print("STOP")


def forward():

    global current_direction
    global robot_status

    GPIO.output(IN1, 1)
    GPIO.output(IN2, 0)

    GPIO.output(IN3, 1)
    GPIO.output(IN4, 0)

    with state_lock:
        current_direction = "forward"

    robot_status = "Moving Forward"

    print("FORWARD")


def backward():

    global current_direction
    global robot_status

    GPIO.output(IN1, 0)
    GPIO.output(IN2, 1)

    GPIO.output(IN3, 0)
    GPIO.output(IN4, 1)

    with state_lock:
        current_direction = "backward"

    robot_status = "Moving Backward"

    print("BACKWARD")


def left():

    global current_direction
    global robot_status

    GPIO.output(IN1, 0)
    GPIO.output(IN2, 1)

    GPIO.output(IN3, 1)
    GPIO.output(IN4, 0)

    with state_lock:
        current_direction = "left"

    robot_status = "Turning Left"

    print("LEFT")


def right():

    global current_direction
    global robot_status

    GPIO.output(IN1, 1)
    GPIO.output(IN2, 0)

    GPIO.output(IN3, 0)
    GPIO.output(IN4, 1)

    with state_lock:
        current_direction = "right"

    robot_status = "Turning Right"

    print("RIGHT")


# =========================
# ULTRASONIC SENSOR
# =========================

def distance():

    GPIO.output(TRIG, False)
    time.sleep(0.05)

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    timeout = time.time()

    while GPIO.input(ECHO) == 0:

        start = time.time()

        if time.time() - timeout > 0.05:
            return 999

    timeout = time.time()

    while GPIO.input(ECHO) == 1:

        stop_time = time.time()

        if time.time() - timeout > 0.05:
            return 999

    elapsed = stop_time - start

    dist = (elapsed * 34300) / 2

    return round(dist, 2)


# =========================
# OBSTACLE MONITOR THREAD
# =========================

def obstacle_monitor():

    global robot_status

    while True:

        with state_lock:
            direction = current_direction

        if direction == "forward":

            d = distance()

            print("Distance:", d, "cm")

            if d < 30:

                robot_status = f"⚠ Obstacle Detected ({d} cm)"

                print("OBSTACLE DETECTED")

                stop()

        time.sleep(0.1)


monitor_thread = threading.Thread(
    target=obstacle_monitor,
    daemon=True
)

monitor_thread.start()

# =========================
# VIDEO STREAM
# =========================

def gen_frames():

    while True:

        frame = picam2.capture_array()

        _, buffer = cv2.imencode(
            '.jpg',
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        )

        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + frame +
            b'\r\n'
        )


# =========================
# ROUTES
# =========================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():

    return Response(
        gen_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/status')
def status():

    try:

        return jsonify({
            "status": robot_status,
            "distance": distance(),
            "direction": current_direction
        })

    except Exception as e:

        return jsonify({
            "status": "Error",
            "error": str(e)
        })


@app.route('/forward')
def move_forward():

    global robot_status

    if distance() < 20:

        robot_status = "⚠ Obstacle Detected"

        stop()

        return jsonify({
            "success": False,
            "message": robot_status
        })

    forward()

    return jsonify({
        "success": True,
        "message": robot_status
    })


@app.route('/backward')
def move_backward():

    backward()

    return jsonify({
        "success": True,
        "message": robot_status
    })


@app.route('/left')
def move_left():

    left()

    return jsonify({
        "success": True,
        "message": robot_status
    })


@app.route('/right')
def move_right():

    right()

    return jsonify({
        "success": True,
        "message": robot_status
    })


@app.route('/stop')
def move_stop():

    stop()

    return jsonify({
        "success": True,
        "message": robot_status
    })


# @app.route('/cam_left')
# def cam_left():

#     global camera_angle
#     global robot_status

#     camera_angle -= 15

#     if camera_angle < -90:
#         camera_angle = -90

#     servo.angle = camera_angle

#     robot_status = f"Camera Angle: {camera_angle}°"

#     return jsonify({
#         "success": True,
#         "message": robot_status
#     })


# @app.route('/cam_right')
# def cam_right():

#     global camera_angle
#     global robot_status

#     camera_angle += 15

#     if camera_angle > 90:
#         camera_angle = 90

#     servo.angle = camera_angle

#     robot_status = f"Camera Angle: {camera_angle}°"

#     return jsonify({
#         "success": True,
#         "message": robot_status
#     })


# =========================
# MAIN
# =========================

if __name__ == '__main__':

    try:

        app.run(
            host='0.0.0.0',
            port=5000,
            threaded=True
        )

    finally:

        stop()
        GPIO.cleanup()