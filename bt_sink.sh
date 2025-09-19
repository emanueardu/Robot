#!/bin/bash
set -e

# Asegurar acceso al servidor de audio del usuario (Pulse/PipeWire)
export XDG_RUNTIME_DIR=/run/user/1000
export PULSE_SERVER=unix:/run/user/1000/pulse/native

# Opcional: si conoces la MAC, seteala via servicio con Environment=BT_MAC=...
BT_MAC="${BT_MAC:-}"

# Si pasaron la MAC, intentamos reconectar (no falla si ya esta conectado)
if [ -n "$BT_MAC" ]; then
  /usr/bin/bluetoothctl connect "$BT_MAC" || true
fi

# Esperar a que aparezca el sink de BlueZ y ponerlo por defecto
for i in {1..40}; do
  SINK="$(pactl list short sinks | awk '/bluez_output/ {print $2; exit}')"
  if [ -n "$SINK" ]; then
    pactl set-default-sink "$SINK" || true
    pactl set-sink-volume   "$SINK" 100% || true
    exit 0
  fi
  sleep 0.5
done

# No abortar si no aparece (el programa igual arranca y puede sonar mas tarde)
exit 0
