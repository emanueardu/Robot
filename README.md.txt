# Proyecto Robot Aspirador Inteligente – Raspberry Pi 5 + ESP32

Este es un proyecto de robot aspirador inteligente desarrollado sobre:

- **Raspberry Pi 5** como unidad central de procesamiento.
- **ESP32** como sensor/actuador.
- **Firebase Realtime Database** como backend para control y monitoreo.
- **MQTT** para comunicación con los módulos de expresiones.

---

## 📂 Estructura del proyecto

- `ojos_mqtt.py`  
  Controla los **OLEDs** y muestra expresiones faciales del robot (ojos, parpadeo, estados). Se comunica por **MQTT** y responde a instrucciones desde Firebase.

- `servos_mqqt.py`  
  Controla dos **servos** que mueven la caja de la cámara y los OLEDs. Permite inclinación desde **-30° (mirando al piso)** hasta **+90° (mirando al techo)**.

- `motores_mqtt.py`  
  Programa que maneja la comunicación **UART** con el ESP32. Recibe datos de sensores (DHT11, ultrasonido, MPU6050, switches, IR) y cambios de estado.

- `firebase_mqtt.py`  
  Envía datos a **Firebase Realtime Database** (estado, sensores, batería, ubicación, etc.).

- `AGENTE_PROMPT.md`  
  Prompt general para usar con **Codex CLI** y mantener el proyecto organizado, modular y optimizado.
- Codigo cargado eb esp32: "ESP32.ino"

---

## 🚀 Ejecución de programas

### Expresiones (OLEDs + MQTT)
```bash
python3 expresiones-mqtt.py
