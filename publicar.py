#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publica las cápsulas en YouTube (Shorts) e Instagram (Stories).

Sin dependencias externas: solo biblioteca estándar y ffmpeg.

- YouTube: sube el mp4 vertical con título, descripción y etiquetas sacados del
  `index-{franja}.json`. YouTube lo trata como Short solo (vertical ≤ 3 min).
- Instagram: una Story es un objeto de 3-60 s, así que la cápsula se parte en dos
  tarjetas. Meta no acepta subida directa: descarga el vídeo de una URL pública, así
  que las partes se suben al Release `capsulas` y se borran al terminar.

Si faltan las credenciales de una red, se salta esa red con un aviso: el resto del
trabajo sigue adelante.

Uso:
    python publicar.py --franja mediodia --dry-run     # ver qué haría
    python publicar.py --franja mediodia --redes youtube,instagram
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "moda-radar/2.0 (+https://github.com)"
RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "docs" / "videos"
REGISTRO = SALIDA / "publicadas.json"
RELEASE = "capsulas"
MAX_STORY = 58          # Meta acepta hasta 60 s; 58 deja margen al contenedor
API_IG = os.environ.get("IG_VERSION") or "v23.0"
PANEL = "https://mexicanfasionstreet-cyber.github.io/moda-radar/"


# --------------------------------------------------------------------------- utilidades

def log(msg):
    print(msg, flush=True)


def http(method, url, data=None, headers=None, timeout=120):
    """Petición JSON sencilla. Devuelve (código, cuerpo decodificado)."""
    h = {"User-Agent": UA}
    h.update(headers or {})
    body = None
    if isinstance(data, dict):
        body = urllib.parse.urlencode(data).encode()
        h.setdefault("Content-Type", "application/x-www-form-urlencoded")
    elif isinstance(data, (bytes, bytearray)):
        body = data
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw.decode("utf-8"))
            except Exception:  # noqa: BLE001
                return r.status, {"raw": raw.decode("utf-8", "ignore")}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(raw)
        except Exception:  # noqa: BLE001
            return e.code, {"raw": raw[:400]}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": f"{type(e).__name__}: {e}"}


def ffmpeg(*args):
    return subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args],
                          capture_output=True, text=True)


def duracion(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        return float(out)
    except Exception:  # noqa: BLE001
        return 0.0


def slug(texto, limite=48):
    limpio = re.sub(r"[^a-zA-Z0-9]+", "-", texto.lower()).strip("-")
    return limpio[:limite].rstrip("-") or "capsula"


# --------------------------------------------------------------------------- metadatos

def cargar_meta(franja, sufijo):
    """Lee el index-{franja}{sufijo}.json de la cápsula."""
    for nombre in (f"index-{franja}{sufijo}.json", f"index{sufijo}.json"):
        p = SALIDA / nombre
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
    return None


def metadatos(meta, fecha, franja, edicion):
    """Título, descripción y etiquetas para YouTube y para el registro."""
    hook = (meta.get("hook") or "").strip()
    titulo = hook if len(hook) <= 95 else hook[:94].rsplit(" ", 1)[0] + "…"
    lineas = [hook, ""]
    for n, it in enumerate(meta.get("items") or [], 1):
        linea = f"{n}. {it.get('headline') or it.get('title')} ({it.get('source')})"
        lineas.append(linea)
        if it.get("link"):
            lineas.append(it["link"])
    etiquetas = "#moda #fashion #industriadelamoda #noticiasdemoda #Shorts"
    if edicion == "latam":
        etiquetas = "#moda #modaMexico #modaLatAm #fashionmexico #Shorts"
    lineas += ["", etiquetas, "", f"The Border Archive · {fecha} · {franja}", PANEL]
    return {
        "titulo": titulo,
        "descripcion": "\n".join(lineas)[:4900],
        "tags": [t for t in etiquetas.replace("#", "").split()],
        "etiquetas": etiquetas,
    }


# --------------------------------------------------------------------------- registro

def ya_publicada(clave):
    try:
        datos = json.loads(REGISTRO.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        datos = {}
    ts = datos.get(clave)
    if not ts:
        return False
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).total_seconds() < 20 * 3600
    except Exception:  # noqa: BLE001
        return False


def marcar_publicada(clave):
    try:
        datos = json.loads(REGISTRO.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        datos = {}
    datos[clave] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    REGISTRO.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


# --------------------------------------------------------------------------- YouTube

def yt_token():
    cid = os.environ.get("YT_CLIENT_ID")
    csec = os.environ.get("YT_CLIENT_SECRET")
    ref = os.environ.get("YT_REFRESH_TOKEN")
    if not (cid and csec and ref):
        return None, "faltan YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN"
    cod, data = http("POST", "https://oauth2.googleapis.com/token", {
        "client_id": cid, "client_secret": csec,
        "refresh_token": ref, "grant_type": "refresh_token",
    })
    if cod == 200 and data.get("access_token"):
        return data["access_token"], "ok"
    return None, f"token: {cod} {str(data)[:160]}"


def yt_estado(video, md, token):
    """videos.insert con resumable devuelve la URL en una cabecera, no en el JSON."""
    cuerpo = {
        "snippet": {
            "title": md["titulo"],
            "description": md["descripcion"],
            "tags": md["tags"][:15],
            "categoryId": "25",
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    datos = json.dumps(cuerpo).encode()
    tam = video.stat().st_size
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        data=datos, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(tam),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            loc = r.headers.get("Location")
    except urllib.error.HTTPError as e:
        return None, f"insert: {e.code} {e.read().decode('utf-8', 'ignore')[:240]}"
    if not loc:
        return None, "insert sin Location"
    put = urllib.request.Request(loc, data=video.read_bytes(), method="PUT", headers={
        "Content-Type": "video/mp4", "Content-Length": str(tam),
    })
    try:
        with urllib.request.urlopen(put, timeout=900) as r:
            out = json.loads(r.read().decode())
        return out.get("id"), "ok"
    except urllib.error.HTTPError as e:
        return None, f"put: {e.code} {e.read().decode('utf-8', 'ignore')[:240]}"
    except Exception as e:  # noqa: BLE001
        return None, f"put: {type(e).__name__}: {e}"


# --------------------------------------------------------------------------- Instagram

def gh_repo():
    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo:
        return repo
    return "mexicanfasionstreet-cyber/moda-radar"


def gh_token():
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def gh_api(method, path, data=None, headers=None):
    tok = gh_token()
    if not tok:
        return 0, {"error": "sin GH_TOKEN"}
    h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
    h.update(headers or {})
    body = json.dumps(data).encode() if isinstance(data, dict) else data
    req = urllib.request.Request(f"https://api.github.com{path}", data=body,
                                 headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {"raw": e.read().decode("utf-8", "ignore")[:300]}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": f"{type(e).__name__}: {e}"}


def release_id():
    repo = gh_repo()
    cod, data = gh_api("GET", f"/repos/{repo}/releases/tags/{RELEASE}")
    if cod == 200 and data.get("id"):
        return data["id"]
    cod, data = gh_api("POST", f"/repos/{repo}/releases",
                       {"tag_name": RELEASE, "name": "Cápsulas", "body": "Vídeos de Moda Radar"})
    if cod in (200, 201) and data.get("id"):
        return data["id"]
    return None


def subir_asset(rid, path, nombre):
    repo = gh_repo()
    datos = path.read_bytes()
    cod, data = gh_api(
        "POST",
        f"/repos/{repo}/releases/{rid}/assets?name={urllib.parse.quote(nombre)}",
        data=datos,
        headers={"Content-Type": "video/mp4", "Content-Length": str(len(datos))},
    )
    if cod in (200, 201):
        return data.get("id"), data.get("browser_download_url")
    return None, None


def borrar_asset(aid):
    repo = gh_repo()
    gh_api("DELETE", f"/repos/{repo}/releases/assets/{aid}")


def partir(video, workdir, segundos=MAX_STORY):
    """Parte el vídeo en trozos de como mucho `segundos`."""
    dur = duracion(video)
    if dur <= segundos:
        return [video]
    n = int(dur // segundos) + 1
    trozo = dur / n
    partes = []
    for i in range(n):
        ini = i * trozo
        largo = min(trozo, dur - ini)
        out = workdir / f"{video.stem}-p{i + 1}.mp4"
        r = ffmpeg("-ss", f"{ini:.3f}", "-i", str(video), "-t", f"{largo:.3f}",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                   "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
                   "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out))
        if r.returncode == 0 and out.exists():
            partes.append(out)
        else:
            log(f"  ! no se pudo cortar el trozo {i + 1}: {r.stderr[:160]}")
    return partes or [video]


def ig_publicar(video_url, token, user_id, espera_max=420):
    """Contenedor STORIES + publicación, con sondeo del estado."""
    cod, data = http("POST", f"https://graph.facebook.com/{API_IG}/{user_id}/media", {
        "media_type": "STORIES",
        "video_url": video_url,
        "access_token": token,
    })
    if cod != 200 or not data.get("id"):
        return None, f"contenedor: {cod} {str(data)[:200]}"
    cid = data["id"]
    inicio = time.time()
    while time.time() - inicio < espera_max:
        time.sleep(8)
        c2, d2 = http("GET",
                      f"https://graph.facebook.com/{API_IG}/{cid}"
                      f"?fields=status_code,status&access_token={token}")
        estado = (d2 or {}).get("status_code")
        if estado == "FINISHED":
            break
        if estado == "ERROR":
            return None, f"Meta rechazó el vídeo: {str(d2)[:200]}"
    else:
        return None, "Meta no terminó de procesar el vídeo a tiempo"
    c3, d3 = http("POST", f"https://graph.facebook.com/{API_IG}/{user_id}/media_publish", {
        "creation_id": cid, "access_token": token,
    })
    if c3 == 200 and d3.get("id"):
        return d3["id"], "ok"
    return None, f"publish: {c3} {str(d3)[:200]}"


# --------------------------------------------------------------------------- principal

def publicar_una(video, md, red, franja, fecha, dry, workdir):
    clave = f"{red}:{video.name}"
    if ya_publicada(clave):
        log(f"  = {red}: ya publicada en las últimas 20 h ({video.name})")
        return True

    if red == "youtube":
        if dry:
            log(f"  · [dry] YouTube ← {video.name} | «{md['titulo']}»")
            return True
        token, err = yt_token()
        if not token:
            log(f"  ! YouTube saltado: {err}")
            return False
        vid, err = yt_estado(video, md, token)
        if vid:
            log(f"  ✓ YouTube: https://youtu.be/{vid}")
            marcar_publicada(clave)
            return True
        log(f"  ! YouTube falló: {err}")
        return False

    if red == "instagram":
        if dry:
            for p in partir(video, workdir, MAX_STORY):
                log(f"  · [dry] Instagram Story ← {p.name} ({duracion(p):.0f} s)")
            return True
        tok = os.environ.get("IG_TOKEN")
        uid = os.environ.get("IG_USER_ID")
        if not tok or not uid:
            log("  ! Instagram saltado: faltan IG_TOKEN / IG_USER_ID")
            return False
        partes = partir(video, workdir, MAX_STORY)
        rid = release_id()
        if not rid:
            log("  ! Instagram: no se pudo preparar el Release para alojar las partes")
            return False
        ok = 0
        for p in partes:
            aid, url = subir_asset(rid, p, p.name)
            if not url:
                log(f"  ! no se pudo alojar {p.name}")
                continue
            try:
                pid, err = ig_publicar(url, tok, uid)
                if pid:
                    log(f"  ✓ Instagram Story: {p.name} ({pid})")
                    ok += 1
                else:
                    log(f"  ! Instagram {p.name}: {err}")
            finally:
                borrar_asset(aid)
        if ok:
            marcar_publicada(clave)
        return ok > 0

    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="Publica las cápsulas en YouTube e Instagram.")
    ap.add_argument("--franja", default="dia", help="dia, manana, mediodia o noche")
    ap.add_argument("--redes", default="youtube,instagram", help="lista separada por comas")
    ap.add_argument("--fecha", default=None, help="AAAA-MM-DD (por defecto, hoy en CDMX)")
    ap.add_argument("--dry-run", action="store_true", help="enseñar qué haría, sin publicar")
    ap.add_argument("--solo-edicion", default=None, choices=["general", "latam"])
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

    fecha = args.fecha
    if not fecha:
        try:
            from zoneinfo import ZoneInfo

            fecha = datetime.now(timezone.utc).astimezone(
                ZoneInfo("America/Mexico_City")).strftime("%Y-%m-%d")
        except Exception:  # noqa: BLE001
            fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    redes = [r.strip() for r in args.redes.split(",") if r.strip()]
    log(f"Publicar {fecha} franja {args.franja} → {', '.join(redes)}")

    workdir = RAIZ / ".tmp" / f"publicar-{os.getpid()}"
    workdir.mkdir(parents=True, exist_ok=True)

    algo = False
    for edicion, sufijo in (("general", ""), ("latam", "-latam")):
        if args.solo_edicion and edicion != args.solo_edicion:
            continue
        video = SALIDA / f"{fecha}-{args.franja}{sufijo}.mp4"
        if not video.exists():
            # la franja "dia" no lleva sufijo de franja
            alt = SALIDA / f"{fecha}{sufijo}.mp4"
            if args.franja == "dia" and alt.exists():
                video = alt
            else:
                log(f"  · {edicion}: no hay vídeo para {fecha}-{args.franja} (se salta)")
                continue
        meta = cargar_meta(args.franja, sufijo) or {}
        md = metadatos(meta, fecha, args.franja, edicion)
        log(f"\n{edicion}: {video.name} · «{md['titulo']}»")
        for red in redes:
            algo = publicar_una(video, md, red, args.franja, fecha, args.dry_run, workdir) or algo
    if not algo:
        log("\nNada publicado en esta pasada.")
    try:
        import shutil

        shutil.rmtree(workdir, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
