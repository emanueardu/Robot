#!/bin/bash
set -e
source /home/emanuel/ojos-env/bin/activate
exec /home/emanuel/ojos-env/bin/python /home/emanuel/motores_mqtt.py >> /home/emanuel/motores_mqtt.log 2>&1
