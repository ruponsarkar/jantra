from flask import Flask, render_template, Response, jsonify, request
import threading
import time

try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import RPi.GPIO as GPIO
except ImportError:
    class FakeGPIO:
        BCM = "BCM"
        OUT = "OUT"
        IN = "IN"
        HIGH = 1
        LOW = 0

        def __init__(self):
            self.outputs = {}

        def setmode(self, mode):
            self.mode = mode

        def setwarnings(self, value):
            self.warnings = value

        def setup(self, pin, mode):
            self.outputs[pin] = self.LOW

        def output(self, pin, value):
            self.outputs[pin] = value

        def input(self, pin):
            return self.outputs.get(pin, self.LOW)

        def cleanup(self):
            self.outputs.clear()

    GPIO = FakeGPIO()

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

picam2 = None

if Picamera2 is not None:
    picam2 = Picamera2()
    try:
        picam2.configure(
            picam2.create_video_configuration(
                main={"size": (1280, 720), "format": "RGB888"},
                buffer_count=2
            )
        )
    except Exception:
        picam2.configure(
            picam2.create_video_configuration(
                main={"size": (1280, 720)},
                buffer_count=2
            )
        )
    picam2.start()

# =========================
# STEPPER MOTOR (28BYJ-48)
# =========================

STEPPER_PINS = {
    "IN1": 27,
    "IN2": 26,
    "IN3": 19,
    "IN4": 13,
}

STEP_SEQUENCE = [
    (1, 0, 0, 0),
    (1, 1, 0, 0),
    (0, 1, 0, 0),
    (0, 1, 1, 0),
    (0, 0, 1, 0),
    (0, 0, 1, 1),
    (0, 0, 0, 1),
    (1, 0, 0, 1),
]

camera_position = 0
camera_lock = threading.Lock()
camera_control_lock = threading.Lock()
camera_motion_direction = None

for pin in STEPPER_PINS.values():
    GPIO.setup(pin, GPIO.OUT)


def apply_step_sequence(step):
    pins = [STEPPER_PINS["IN1"], STEPPER_PINS["IN2"], STEPPER_PINS["IN3"], STEPPER_PINS["IN4"]]

    for pin, value in zip(pins, step):
        GPIO.output(pin, value)


def move_camera(direction="left", steps=20, delay=0.002):
    global camera_position
    global robot_status

    if direction not in ["left", "right"]:
        raise ValueError("direction must be 'left' or 'right'")

    sequence = list(STEP_SEQUENCE)

    if direction == "right":
        sequence.reverse()

    with camera_lock:
        for _ in range(steps):
            for step in sequence:
                apply_step_sequence(step)
                time.sleep(delay)

        camera_position += -steps if direction == "left" else steps
        robot_status = f"Camera moved {direction} ({abs(camera_position)} steps)"
        apply_step_sequence((0, 0, 0, 0))

    return camera_position


def set_camera_direction(direction):
    global camera_motion_direction

    with camera_control_lock:
        camera_motion_direction = direction
        if direction is None:
            with camera_lock:
                apply_step_sequence((0, 0, 0, 0))


def camera_motion_worker():
    global camera_position
    global robot_status

    while True:
        with camera_control_lock:
            direction = camera_motion_direction
            if direction is not None:
                sequence = STEP_SEQUENCE if direction == "left" else reversed(STEP_SEQUENCE)

                with camera_lock:
                    for step in sequence:
                        apply_step_sequence(step)
                        time.sleep(0.002)

                    camera_position += -1 if direction == "left" else 1
                    robot_status = f"Camera moved {direction} ({abs(camera_position)} steps)"
                continue

        time.sleep(0.01)


threading.Thread(target=camera_motion_worker, daemon=True).start()

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

        if frame is None:
            continue

        _, buffer = cv2.imencode(
            '.jpg',
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        )

        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + frame +
            b'\r\n'
        )
        time.sleep(1 / 15)


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
            "direction": current_direction,
            "camera_position": camera_position
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


@app.route('/cam_left')
def cam_left():

    set_camera_direction("left")

    return jsonify({
        "success": True,
        "message": robot_status
    })


@app.route('/cam_right')
def cam_right():

    set_camera_direction("right")

    return jsonify({
        "success": True,
        "message": robot_status
    })


@app.route('/cam_stop')
def cam_stop():

    set_camera_direction(None)

    return jsonify({
        "success": True,
        "message": "Camera stopped"
    })


@app.route('/cam_center')
def cam_center():

    global camera_position
    global robot_status

    set_camera_direction(None)

    with camera_lock:
        steps = abs(camera_position)
        if steps == 0:
            robot_status = "Camera already centered"
            return jsonify({
                "success": True,
                "message": robot_status
            })

        direction = "right" if camera_position < 0 else "left"

    move_camera(direction, steps=steps)

    return jsonify({
        "success": True,
        "message": robot_status
    })


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