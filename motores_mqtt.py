# -*- coding: utf-8 -*-
import json
import serial
import paho.mqtt.client as mqtt
import threading

# ===== UART =====
SERIAL_PORT = "/dev/serial0"   # Ajustar según conexión
BAUDRATE = 115200
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0.1)

# ===== MQTT =====
TOPIC_CMD    = "motores/cmd"      # comandos desde cerebro
TOPIC_SENS   = "esp32/sensors"    # lecturas de sensores
TOPIC_EVENTS = "esp32/events"     # eventos (bumper, cliff)
TOPIC_ACK    = "esp32/ack"        # respuestas OK/ERR

# ===== Funciones =====
def send_uart(cmd: str):
    """Manda comando crudo a la ESP32"""
    ser.write((cmd.strip() + "\n").encode("utf-8"))
    print("? TX:", cmd.strip())

def handle_command(payload: str):
    """Parsea mensaje MQTT y lo traduce a UART"""
    try:
        data = json.loads(payload)
    except Exception:
        print("?? Comando no es JSON:", payload)
        return

    t = data.get("type", "")
    if t == "move":
        L = int(data.get("L", 0))
        R = int(data.get("R", 0))
        send_uart(f"M {L} {R}")
    elif t == "stop":
        send_uart("STOP")
    elif t == "vac":
        send_uart("V" if data.get("on", True) else "v")  # toggle simple
    elif t == "brush":
        send_uart("B" if data.get("on", True) else "b")  # toggle simple
    elif t == "status":
        send_uart("S")
    else:
        print("?? Tipo de comando desconocido:", data)

def uart_reader():
    """Hilo lector UART"""
    while True:
        try:
            line = ser.readline().decode("utf-8").strip()
            if not line:
                continue
            print("? RX:", line)

            if line.startswith("SENS "):
                # Quitar prefijo y publicar JSON
                try:
                    payload = line[5:]
                    client.publish(TOPIC_SENS, payload, qos=0, retain=False)
                except Exception as e:
                    print("?? Error parseando SENS:", e)

            elif line.startswith("EVENT "):
                try:
                    payload = line[6:]
                    client.publish(TOPIC_EVENTS, payload, qos=0, retain=False)
                except Exception as e:
                    print("?? Error parseando EVENT:", e)

            else:
                # Respuestas como OK M, ERR CMD...
                client.publish(TOPIC_ACK, json.dumps({"resp": line}))

        except Exception as e:
            print("?? Error UART:", e)

# ===== MQTT callbacks =====
def on_connect(client, userdata, flags, rc, props=None):
    client.subscribe(TOPIC_CMD)
    print("? Motores MQTT conectado, escuchando en", TOPIC_CMD)

def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    print(f"[MQTT] {msg.topic} = {payload}")
    handle_command(payload)

# ===== Main =====
client = mqtt.Client(client_id="motores", protocol=mqtt.MQTTv5)
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883, 60)

# Hilo lector UART
threading.Thread(target=uart_reader, daemon=True).start()

client.loop_forever()
