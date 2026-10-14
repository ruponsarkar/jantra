import argparse
import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    class FakeGPIO:
        BCM = "BCM"
        OUT = "OUT"
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

        def cleanup(self):
            self.outputs.clear()

    GPIO = FakeGPIO()


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


def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for pin in STEPPER_PINS.values():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, 0)


def apply_step(step):
    pins = [
        STEPPER_PINS["IN1"],
        STEPPER_PINS["IN2"],
        STEPPER_PINS["IN3"],
        STEPPER_PINS["IN4"],
    ]

    for pin, value in zip(pins, step):
        GPIO.output(pin, value)


def release_motor():
    apply_step((0, 0, 0, 0))


def move(direction, steps, delay):
    if direction not in {"left", "right"}:
        raise ValueError("direction must be 'left' or 'right'")

    sequence = list(STEP_SEQUENCE)
    if direction == "right":
        sequence.reverse()

    for _ in range(steps):
        for step in sequence:
            apply_step(step)
            time.sleep(delay)

    release_motor()


def sweep(steps, delay, pause):
    print(f"Sweeping left for {steps} steps")
    move("left", steps, delay)
    time.sleep(pause)
    print(f"Sweeping right for {steps} steps")
    move("right", steps, delay)


def parse_args():
    parser = argparse.ArgumentParser(description="Stepper motor hardware test")
    parser.add_argument(
        "action",
        choices=["left", "right", "sweep"],
        nargs="?",
        default="sweep",
        help="motor movement to perform",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=128,
        help="number of step cycles to run",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.002,
        help="delay between half-steps in seconds",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.5,
        help="pause between sweep directions in seconds",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    setup_gpio()

    try:
        if args.action == "sweep":
            sweep(args.steps, args.delay, args.pause)
        else:
            print(f"Moving {args.action} for {args.steps} steps")
            move(args.action, args.steps, args.delay)
    finally:
        release_motor()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
