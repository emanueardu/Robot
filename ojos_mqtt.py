# -*- coding: utf-8 -*-
import time
import json
import random
import threading
import paho.mqtt.client as mqtt
from PIL import Image, ImageDraw

# ==== IMPORTA tus funciones de dibujo ====
# normal(), close(), angry(), surprised(), etc.
from ojos_expresiones import normal, close, angry, surprised

# ===== MQTT =====
BROKER = "localhost"
TOPIC_CMD = "ojos/expresion"

# ===== Estado global =====
current_expr = "boot"     # estado inicial
last_update = time.time() # último comando recibido

# ===== Función para mostrar expresiones =====
def set_expression(expr):
    global current_expr, last_update
    current_expr = expr
    last_update = time.time()

    if expr == "normal":
        normal()
    elif expr == "close":
        close()
    elif expr == "angry":
        angry()
    elif expr == "surprised":
        surprised()
    elif expr == "boot":
        close()
    else:
        normal()

# ===== MQTT callbacks =====
def on_connect(client, userdata, flags, rc, props=None):
    client.subscribe(TOPIC_CMD)
    print("? Ojos conectado al broker MQTT")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"[MQTT] {msg.topic} = {payload}")
    set_expression(payload)

client = mqtt.Client(client_id="ojos", protocol=mqtt.MQTTv5)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, 1883, 60)

# ===== Animación de arranque =====
def boot_sequence():
    set_expression("boot")
    time.sleep(1)
    for _ in range(3):  # parpadea 3 veces
        close()
        time.sleep(0.3)
        normal()
        time.sleep(0.3)
    set_expression("normal")

# ===== Loop de parpadeo / timeout =====
def eyes_loop():
    global current_expr, last_update
    boot_sequence()
    while True:
        now = time.time()

        # Si pasó más de 60s sin comandos ? volver a normal
        if now - last_update > 60 and current_expr != "normal":
            set_expression("normal")

        # Si está en normal ? parpadea de vez en cuando
        if current_expr == "normal" and random.random() < 0.02:  # ~2% chance cada ciclo
            close()
            time.sleep(0.2)
            normal()

        time.sleep(0.1)

threading.Thread(target=eyes_loop, daemon=True).start()

client.loop_forever()



