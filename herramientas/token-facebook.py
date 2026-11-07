#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Saca el IG_USER_ID y un token que no caduca, usando la app de Facebook.

No necesita portafolio comercial. Hace tres cosas:
  1. cambia el token corto de Graph API Explorer por uno de larga duración
  2. lista tus páginas de Facebook y te deja elegir
  3. del Instagram vinculado a esa página saca el ID y el token de página

Uso:
    python herramientas/token-facebook.py

Te pedirá tres cosas: el ID de la app, el secreto de la app y el token corto
(ese lo generas en https://developers.facebook.com/tools/explorer/ seleccionando
la app radar-moda y marcando los permisos instagram_basic, instagram_content_publish,
pages_show_list y pages_read_engagement).
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://graph.facebook.com/v23.0"


def get(path, **params):
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": json.loads(e.read().decode() or "{}")}


def pedir(etiqueta):
    valor = input(f"{etiqueta}: ").strip()
    return valor


def main():
    print("\nDatos de la app (developers.facebook.com → radar-moda → Configuración → Básica)\n")
    app_id = pedir("ID de la app")
    app_secret = pedir("Clave secreta de la app")
    corto = pedir("Token corto de Graph API Explorer")

    print("\n1. Cambiando el token por uno de larga duración…")
    d = get("oauth/access_token", grant_type="fb_exchange_token",
            client_id=app_id, client_secret=app_secret, fb_exchange_token=corto)
    largo = d.get("access_token")
    if not largo:
        print(f"   Falló: {d}")
        return 1
    print("   ok")

    print("2. Buscando tus páginas de Facebook…")
    d = get("me/accounts", access_token=largo, fields="id,name,access_token,instagram_business_account")
    paginas = d.get("data") or []
    if not paginas:
        print(f"   No hay páginas accesibles. Respuesta: {d}")
        return 1
    for i, p in enumerate(paginas, 1):
        tiene = "con Instagram" if p.get("instagram_business_account") else "sin Instagram"
        print(f"   {i}. {p['name']} ({tiene})")

    if len(paginas) == 1:
        elegida = paginas[0]
    else:
        try:
            n = int(input(f"\n¿Cuál es la página? (1-{len(paginas)}): ").strip())
            elegida = paginas[n - 1]
        except Exception:  # noqa: BLE001
            print("   Opción no válida.")
            return 1

    ig = (elegida.get("instagram_business_account") or {}).get("id")
    if not ig:
        print("\nEsa página no tiene una cuenta de Instagram vinculada.")
        print("Vincúlala en Instagram: Configuración → Cuenta → Compartir en Facebook,")
        print("o en la página: Configuración → Instagram → Conectar cuenta.")
        return 1

    print("\n¡Listo! Guarda estos dos secretos en GitHub")
    print("(Settings → Secrets and variables → Actions):\n")
    print(f"  IG_USER_ID = {ig}")
    print(f"  IG_TOKEN   = {elegida.get('access_token')}\n")
    print("Y crea una variable llamada IG_HOST con el valor graph.facebook.com")
    print("(Settings → Secrets and variables → Actions → pestaña Variables).\n")
    print("El token de página no caduca mientras la app siga existiendo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
