# -*- coding: utf-8 -*-
import json
import time
import threading
import paho.mqtt.client as mqtt
import firebase_admin
from firebase_admin import credentials, db

# ===== Firebase setup =====
cred = credentials.Certificate("/home/emanuel/firebase-key.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://robertito-71b91-default-rtdb.firebaseio.com"
})

# Paths en Firebase
PATH_STATE = "/robot/state"
PATH_CMD   = "/robot/cmd"
PATH_EVENTS = "/robot/events"

# ===== MQTT setup =====
BROKER = "localhost"
TOPICS = [
    ("ojos/state",0),
    ("servos/state",0),
    ("esp32/#",0)
]

def publish_to_firebase(path, data):
    """Escribe un JSON en Firebase"""
    try:
        ref = db.reference(path)
        ref.set(data)
        print("? Firebase", path, data)
    except Exception as e:
        print("?? Error Firebase:", e)

def push_event(event_type, data):
    """Guarda un evento con timestamp en Firebase"""
    try:
        ref = db.reference(PATH_EVENTS + "/" + event_type)
        payload = {
            "timestamp": int(time.time()),
            "data": data
        }
        ref.push(payload)   # se agrega como histórico
        print("? Firebase EVENT", event_type, payload)
    except Exception as e:
        print("?? Error guardando evento:", e)

# ===== MQTT callbacks =====
def on_connect(client, userdata, flags, rc, props=None):
    client.subscribe(TOPICS)
    print("? Firebase-MQTT conectado al broker")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    topic = msg.topic
    print(f"[MQTT] {topic} = {payload}")

    try:
        data = json.loads(payload)
    except Exception:
        data = {"raw": payload}

    if topic.startswith("esp32/events"):
        # Guardar como evento con timestamp
        event_type = topic.split("/")[-1]  # ej: bumperL, cliff
        push_event(event_type, data)
    else:
        # Guardar en state
        path = PATH_STATE + "/" + topic.replace("/", "_")
        publish_to_firebase(path, data)

client = mqtt.Client(client_id="firebase", protocol=mqtt.MQTTv5)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, 1883, 60)

# ===== Firebase ? MQTT (escuchar comandos) =====
def firebase_listener(event):
    """Se dispara cuando cambia /robot/cmd"""
    if event.data is None:
        return
    try:
        print("? Firebase CMD:", event.data)
        for k,v in event.data.items():
            if k == "ojos":
                client.publish("ojos/expresion", v)
            elif k == "servos":
                client.publish("servos/angle", json.dumps(v))
            elif k == "motores":
                client.publish("motores/cmd", json.dumps(v))
    except Exception as e:
        print("?? Error manejando comando Firebase:", e)

def start_firebase_watch():
    ref = db.reference(PATH_CMD)
    ref.listen(firebase_listener)

threading.Thread(target=start_firebase_watch, daemon=True).start()

client.loop_forever()


