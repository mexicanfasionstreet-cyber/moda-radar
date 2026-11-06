#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consigue el YT_REFRESH_TOKEN para publicar en YouTube (una sola vez).

Usa el flujo de dispositivo de Google: no hace falta servidor ni navegador en esta
máquina, solo autorizar un código desde el móvil.

Antes de ejecutarlo necesitas un cliente OAuth de tipo
"TVs and Limited Input devices" en https://console.cloud.google.com/apis/credentials
(con la YouTube Data API v3 habilitada en el proyecto).

Uso:
    set YT_CLIENT_ID=...    (PowerShell: $env:YT_CLIENT_ID="...")
    set YT_CLIENT_SECRET=...
    python herramientas/token-youtube.py

Copia el refresh_token que imprime al final y guárdalo como secreto del repo.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SCOPE = "https://www.googleapis.com/auth/youtube.upload"
DEVICE = "https://oauth2.googleapis.com/device/code"
TOKEN = "https://oauth2.googleapis.com/token"


def post(url, datos):
    cuerpo = urllib.parse.urlencode(datos).encode()
    req = urllib.request.Request(url, data=cuerpo, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def main():
    cid = os.environ.get("YT_CLIENT_ID") or (sys.argv[1] if len(sys.argv) > 1 else "")
    csec = os.environ.get("YT_CLIENT_SECRET") or (sys.argv[2] if len(sys.argv) > 2 else "")
    if not cid or not csec:
        print("Faltan YT_CLIENT_ID y YT_CLIENT_SECRET.")
        print("Créalos en https://console.cloud.google.com/apis/credentials")
        return 1

    cod, data = post(DEVICE, {"client_id": cid, "scope": SCOPE})
    if cod != 200:
        print(f"No se pudo iniciar el flujo: {cod} {data}")
        return 1

    print("\n1. Abre esta dirección en el móvil o en cualquier navegador:")
    print(f"   {data['verification_url']}")
    print(f"2. Escribe este código: {data['user_code']}")
    print("3. Autoriza con la cuenta que tiene el canal de YouTube.\n")
    print("Esperando autorización…")

    intervalo = int(data.get("interval", 5))
    limite = time.time() + int(data.get("expires_in", 1800))
    while time.time() < limite:
        time.sleep(intervalo)
        c, r = post(TOKEN, {
            "client_id": cid,
            "client_secret": csec,
            "device_code": data["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        if c == 200:
            print("\nAutorizado.\n")
            print("Guarda estos dos secretos en el repositorio")
            print("(Settings → Secrets and variables → Actions):\n")
            print(f"  YT_REFRESH_TOKEN = {r['refresh_token']}")
            print(f"  YT_CLIENT_ID     = {cid}")
            print("  YT_CLIENT_SECRET = (el que ya tienes)\n")
            return 0
        error = (r or {}).get("error", "")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            intervalo += 2
            continue
        print(f"\nFalló: {c} {r}")
        return 1

    print("\nSe agotó el tiempo. Vuelve a empezar.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
