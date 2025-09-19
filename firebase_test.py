# -*- coding: utf-8 -*-
import firebase_admin
from firebase_admin import credentials, db

# Ruta al JSON de credenciales
cred = credentials.Certificate("/home/emanuel/firebase-key.json")

# ?? reemplazá con tu URL real de Realtime Database
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://robertito-71b91-default-rtdb.firebaseio.com"
})

# Referencia a la ruta donde queremos escribir
ref = db.reference("/robot/test")

# Escribir un valor
ref.set("ok")
print("? Valor escrito en /robot/test = 'ok'")

# Leer el valor recién escrito
val = ref.get()
print("Valor leido de Firebase:", val)
