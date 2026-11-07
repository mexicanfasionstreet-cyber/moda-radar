#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convierte un token de Instagram en uno de larga duración (60 días).

Úsalo si el token que copiaste del panel de Meta caduca en una hora. También sirve
para renovarlo cada dos meses sin volver a crear la app.

Uso:
    python herramientas/token-instagram.py TU_TOKEN_AQUI

Imprime el token de 60 días: ese es el que va en el secreto IG_TOKEN.
"""

import json
import sys
import urllib.error
import urllib.request

HOST = "https://graph.instagram.com"


def main():
    if len(sys.argv) < 2:
        print("Uso: python herramientas/token-instagram.py TU_TOKEN")
        print("\nEl token lo copias del panel de Meta: tu app → Instagram → API setup")
        return 1

    corto = sys.argv[1].strip()
    url = (f"{HOST}/access_token?grant_type=ig_exchange_token"
           f"&client_secret=&access_token={corto}")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Falló: {e.code} {e.read().decode('utf-8', 'ignore')[:300]}")
        return 1

    token = d.get("access_token")
    if not token:
        print(f"Respuesta inesperada: {d}")
        return 1

    dias = d.get("expires_in", 0) // 86400
    print("\nToken de larga duración:\n")
    print(f"  IG_TOKEN = {token}\n")
    print(f"Caduca en ~{dias} días. Guárdalo como secreto IG_TOKEN del repositorio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
