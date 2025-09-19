# -*- coding: utf-8 -*-
import json
from time import sleep
from gpiozero import Servo
import paho.mqtt.client as mqtt

# Pines BCM (por defecto)
SERVO_A_PIN = 17
SERVO_B_PIN = 27

# Pulsos hobby típicos (ajustables)
MIN_PW = 0.5/1000
MAX_PW = 2.5/1000

# Rango visual en grados
MIN_ANGLE = -30   # piso
MAX_ANGLE = 90    # techo

# Offsets por calibración mecánica
A_OFFSET = 0
B_OFFSET = 0

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def angle_to_value(angle):
    # Mapea de [-30..90] a [-1..1]
    norm = (angle - MIN_ANGLE) / float(MAX_ANGLE - MIN_ANGLE)
    return (norm * 2.0) - 1.0

def visual_to_servo_angles(theta, mirror=True):
    # Servo A sigue theta; Servo B espejado si mirror=True
    a = clamp(theta + A_OFFSET, MIN_ANGLE, MAX_ANGLE)
    b_theta = (-theta if mirror else theta)
    b = clamp(b_theta + B_OFFSET, MIN_ANGLE, MAX_ANGLE)
    return a, b

def release_pwm(servo_obj):
    if hasattr(servo_obj, "detach"):
        servo_obj.detach()
    else:
        servo_obj.close()

def move_once(theta, wait=0.6, mirror=True, hold=False):
    servo_a = Servo(SERVO_A_PIN, min_pulse_width=MIN_PW, max_pulse_width=MAX_PW)
    servo_b = Servo(SERVO_B_PIN, min_pulse_width=MIN_PW, max_pulse_width=MAX_PW)

    a_deg, b_deg = visual_to_servo_angles(theta, mirror=mirror)
    servo_a.value = angle_to_value(a_deg)
    servo_b.value = angle_to_value(b_deg)
    sleep(wait)

    if not hold:
        release_pwm(servo_a)
        release_pwm(servo_b)

# ================== MQTT ==================
TOPIC_CMD = "servos/angle"
TOPIC_STATE = "servos/state"

def handle_command(payload: str):
    """Parsea mensaje y ejecuta movimiento"""
    try:
        data = json.loads(payload)
        theta = float(data.get("angle", 0))
        wait = float(data.get("wait", 0.6))
        mirror = bool(data.get("mirror", True))
        hold = bool(data.get("hold", False))
    except Exception:
        # Si no es JSON, intentar parsear como ángulo directo
        theta = float(payload)
        wait = 0.6
        mirror = True
        hold = False

    theta = clamp(theta, MIN_ANGLE, MAX_ANGLE)
    move_once(theta, wait, mirror=mirror, hold=hold)

    state = {"angle": theta, "mirror": mirror, "hold": hold}
    client.publish(TOPIC_STATE, json.dumps(state), qos=0, retain=False)

def on_connect(client, userdata, flags, rc, props=None):
    client.subscribe(TOPIC_CMD)
    print("? Servos MQTT conectado, esperando comandos en", TOPIC_CMD)

def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    print(f"[MQTT] {msg.topic} = {payload}")
    handle_command(payload)

client = mqtt.Client(client_id="servos", protocol=mqtt.MQTTv5)
client.on_connect = on_connect
client.on_message = on_message
client.reconnect_delay_set(min_delay=1, max_delay=5)
client.connect("localhost", 1883, 60)
client.loop_forever()
