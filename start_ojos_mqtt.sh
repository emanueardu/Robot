#!/bin/bash
set -e
source /home/emanuel/ojos-env/bin/activate
exec /home/emanuel/ojos-env/bin/python /home/emanuel/ojos_mqtt.py >> /home/emanuel/ojos_mqtt.log 2>&1
