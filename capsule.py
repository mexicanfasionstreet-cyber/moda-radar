#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cápsula diaria de Moda Radar.

Toma las noticias con mejor puntuación de la edición del día y produce un vídeo
vertical de ~45 s: imágenes de los artículos, titulares en pantalla y voz en off.

Flujo:
  1. selecciona 5 noticias (una por sección, con imagen a ser posible)
  2. escribe el guion: con IA si hay clave, si no con plantilla
  3. sintetiza la voz (edge-tts) y mide la duración real de cada frase
  4. compone cada diapositiva (foto + degradado + titular + marca)
  5. monta con ffmpeg: paneo lento sobre la foto, texto fijo, audio sincronizado
  6. guarda docs/videos/AAAA-MM-DD.mp4 y la portada, y rota los antiguos

Uso:
    python capsule.py                 # genera la cápsula de la edición de hoy
    python capsule.py --tts silent    # sin voz (para probar el montaje)
    python capsule.py --dry-run       # solo enseña el guion y los minutos
"""

from __future__ import annotations

import argparse
import hashlib
import asyncio
import html as htmllib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1080, 1920          # vertical 9:16
ZOOM_W, ZOOM_H = 1188, 2112  # 10% extra para que el paneo no deje bordes
FPS = 30
MAX_ITEMS = 5
KEEP_VIDEOS = 10
VOICE = os.environ.get("CAPSULE_VOICE") or "es-MX-DaliaNeural"
RATE = os.environ.get("CAPSULE_RATE") or "+5%"
ACCENT = (255, 77, 109)
BG = (10, 10, 12)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

FONTS_BOLD = [
    "C:/Windows/Fonts/seguisb.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONTS_REG = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

SECTION_LABEL = {
    "negocio": "Negocio",
    "retail": "Retail",
    "pasarela": "Pasarela",
    "sostenibilidad": "Sostenibilidad",
    "belleza": "Belleza",
    "personas": "Movimientos",
    "cultura": "Cultura",
    "diseno": "Diseño",
    "calzado": "Calzado",
    "industria": "Industria",
}


# --------------------------------------------------------------------------- utilidades

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def ffprobe_duration(path):
    out = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    ]).stdout.strip()
    return float(out or 0)


def load_font(size, bold=True):
    for path in (FONTS_BOLD if bold else FONTS_REG):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def wrap(draw, text, font, max_width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_headline(draw, text, max_width, max_lines, sizes=(76, 68, 60, 54, 48, 42)):
    for size in sizes:
        font = load_font(size, bold=True)
        lines = wrap(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
    font = load_font(sizes[-1], bold=True)
    return font, wrap(draw, text, font, max_width)[:max_lines]


TRAILING = {
    "a", "al", "de", "del", "en", "con", "por", "para", "que", "y", "o", "el", "la",
    "los", "las", "un", "una", "unos", "unas", "su", "sus", "lo", "se", "como", "más",
}


def short_title(title, words=8):
    """Titular de pantalla: recorta sin dejar preposiciones colgando."""
    clean = re.sub(r"\s+", " ", title).strip().rstrip(" .;:")
    parts = clean.split(" ")
    if len(parts) <= words:
        return clean
    cut = parts[:words]
    while len(cut) > 3 and cut[-1].lower().strip(",;:") in TRAILING:
        cut.pop()
    return " ".join(cut).rstrip(",;:.") + "…"


# --------------------------------------------------------------------------- traducción

_TR_CACHE = {}


def translate_es(text):
    """Traduce al español sin clave (Google gtx). Devuelve '' si falla."""
    text = (text or "").strip()
    if not text:
        return ""
    if text in _TR_CACHE:
        return _TR_CACHE[text]
    q = urllib.parse.quote(text[:1400])
    url = (
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=auto&tl=es&dt=t&q={q}"
    )
    for intento in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8"))
            out = "".join(p[0] for p in data[0] if p[0]).strip()
            if out:
                _TR_CACHE[text] = out
                return out
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.7 * (intento + 1))  # Google corta si se piden muchas seguidas
    print(f"  ! no se pudo traducir: {text[:60]}")
    return ""


# --------------------------------------------------------------------------- imagen desde la página

_CHARSET_RX = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?([A-Za-z0-9_-]+)""", re.I)


def decode_html(raw, header_charset=None):
    """Texto de una página respetando su codificación (hay sitios en latin-1/cp1252:
    leerlos como UTF-8 se come los acentos: "Edicin reuni")."""
    m = _CHARSET_RX.search(raw[:4096])
    for cs in (header_charset, m.group(1).decode("ascii", "ignore") if m else None):
        if cs:
            try:
                return raw.decode(cs)
            except Exception:  # noqa: BLE001
                pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def _es_google(link):
    """Los enlaces de news.google.com redirigen con JavaScript: su HTML es de Google."""
    return "news.google." in (link or "")


META_IMG = re.compile(
    r"""<meta[^>]+(?:property|name)\s*=\s*["'](?:og:image|twitter:image)["']"""
    r"""[^>]+content\s*=\s*["']([^"']+)["']""",
    re.I,
)


def og_image(link):
    """Busca la imagen de portada en el HTML del artículo (muchos RSS no la traen)."""
    if _es_google(link):
        return None
    try:
        req = urllib.request.Request(link, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = decode_html(r.read(600000), r.headers.get_content_charset())
        m = META_IMG.search(raw)
        if m:
            return htmllib.unescape(m.group(1))
    except Exception:  # noqa: BLE001
        pass
    return None


META_DESC = re.compile(
    r"""<meta[^>]+(?:property|name)\s*=\s*["'](?:og:description|description)["']"""
    r"""[^>]+content\s*=\s*["']([^"']+)["']""",
    re.I,
)


def page_description(link):
    """Entradilla de la página, para noticias cuyo RSS no trae resumen."""
    if _es_google(link):
        return ""
    try:
        req = urllib.request.Request(link, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = decode_html(r.read(600000), r.headers.get_content_charset())
        m = META_DESC.search(raw)
        if m:
            txt = htmllib.unescape(m.group(1)).strip()
            txt = re.sub(r"\s+", " ", txt)
            if len(txt) > 40:
                return txt
    except Exception:  # noqa: BLE001
        pass
    return ""


def resolve_images(items, limit=14):
    """Completa con og:image las noticias sin foto antes de seleccionar."""
    faltan = sorted(
        [it for it in items if not it.get("image")],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )
    hechas = 0
    for it in faltan:
        if hechas >= limit:
            break
        hechas += 1
        img = og_image(it["link"])
        if img:
            it["image"] = img
    return sum(1 for it in items if it.get("image"))


# --------------------------------------------------------------------------- selección

# piezas que no son noticia: opinión, galerías de fotos, crónicas de fiestas.
# Los titulares llegan en inglés y en español, así que el patrón cubre ambos.
FLUFF = re.compile(
    r"(opini[oó]n|op-ed|editorial|galer[ií]a|in pictures|photo gallery|photos:|"
    r"\binside\b|as[ií] fue|dentro de la|todo lo que|lo que (vimos|sabemos)|"
    r"photocall|recap:)",
    re.I,
)

# la cápsula es de industria: el negocio manda sobre la pasarela o la cultura
CAT_BONUS = {
    "negocio": 1.6, "retail": 1.3, "sostenibilidad": 0.9, "personas": 0.7,
    "industria": 0.5, "calzado": 0.4, "diseno": 0.3, "pasarela": 0.2,
    "belleza": 0.1, "cultura": 0.0,
}


# en la edición de México y LatAm lo interesante es la escena local: diseñadores,
# desfiles y fashion weeks pesan casi tanto como el negocio
CAT_BONUS_LATAM = {
    "negocio": 1.2, "retail": 1.0, "pasarela": 1.0, "diseno": 0.9, "personas": 0.7,
    "sostenibilidad": 0.7, "industria": 0.5, "calzado": 0.3, "belleza": 0.2, "cultura": 0.2,
}

# regiones de los medios de la región (igual que el botón "México y LatAm" del panel)
LATAM_REGIONS = {"mx", "latam", "ar", "co", "cl", "pe", "br", "uy", "ve", "ec", "gt", "cr"}
# una noticia de un medio internacional entra si el titular habla de la región
LATAM_RX = re.compile(
    r"\b(m[eé]xic\w*|mexican\w*|latinoam[eé]ric\w*|latin america\w*|latam|tijuana|monterrey"
    r"|guadalajara|cdmx|ciudad de m[eé]xico|baja california|colombia\w*|argentin\w*"
    r"|per[uú]\b|peruan\w*|brasil\w*|brazil\w*|bogot[aá]|medell[ií]n|buenos aires"
    r"|palacio de hierro|coppel|falabella|inexmoda|colombiamoda)",
    re.I,
)


def es_latam(it):
    if it.get("region") in LATAM_REGIONS:
        return True
    return bool(LATAM_RX.search(it.get("title", "")))


EDICIONES = {
    "general": {
        "sufijo": "",
        "filtro": None,
        "bonus": CAT_BONUS,
        "kicker": "Hoy",
        "portada": "Lo que mueve la moda hoy",
        "enfoque": "la industria de la moda",
        "extra": "",
        "hook": "Estas son las noticias que mueven hoy la industria de la moda.",
        "outro": "Eso es todo por hoy. Mañana, más moda.",
        "tag": "",
        "cierre": "{fecha}",
    },
    "latam": {
        "sufijo": "-latam",
        "filtro": es_latam,
        "bonus": CAT_BONUS_LATAM,
        "kicker": "México y LatAm",
        "portada": "La moda en México y Latinoamérica",
        "enfoque": "la moda en México y Latinoamérica",
        "extra": "- Di el país o la ciudad cuando la noticia lo indique.\n",
        "hook": "Esto es lo que pasa hoy en la moda de México y Latinoamérica.",
        "outro": "Eso es todo por hoy. Mañana, más moda latina.",
        "tag": "MX · LATAM",
        # las notas de Tijuana y Baja California tienen lugar reservado (hasta 2)
        "prioridad": re.compile(r"tijuana|baja california|ensenada|mexicali|rosarito|tecate", re.I),
        "prioridad_max": 2,
        "cierre": "México y LatAm · {fecha}",
    },
}
ED = EDICIONES["general"]  # edición activa; main() la cambia con --edicion


_SIM_SKIP = {"tijuana", "mexico", "moda", "baja", "california", "fashion", "desfile", "pasarela"}


def _palabras(it):
    import unicodedata
    t = unicodedata.normalize("NFKD", it.get("title", "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]{5,}", t) if w not in _SIM_SKIP}


def mismo_evento(a, b):
    """Dos titulares sobre lo mismo ("El Trompo conmemoró…" / "El Trompo celebra…")."""
    return len(_palabras(a) & _palabras(b)) >= 2


def reserve_priority(picked, items, regex, maximo):
    """Garantiza hasta `maximo` noticias que casan con `regex` (sin repetir evento)."""
    def es_prio(it):
        return bool(regex.search(f"{it.get('title', '')} {it.get('excerpt', '')}")) or it.get("source") == "Tijuana"

    elegidas = [it for it in picked if es_prio(it)]
    for it in sorted((x for x in items if es_prio(x)), key=lambda x: x.get("score", 0), reverse=True):
        if len(elegidas) >= maximo:
            break
        if it in elegidas or any(mismo_evento(it, e) for e in elegidas):
            continue
        elegidas.append(it)
    nuevas = [it for it in elegidas if it not in picked]
    # sustituyen a las últimas noticias que no son prioritarias
    for it in nuevas:
        for k in range(len(picked) - 1, -1, -1):
            if not es_prio(picked[k]):
                picked[k] = it
                break
    return picked


def pick_items(items, n=MAX_ITEMS, bonus=None):
    """Noticias con imagen primero, variedad de secciones y peso de negocio."""
    bonus = CAT_BONUS if bonus is None else bonus

    def peso(it):
        sec = it["tags"][0] if it.get("tags") else "industria"
        return it.get("score", 0) + bonus.get(sec, 0)

    con_img = [it for it in items if it.get("image")]
    utiles = [
        it for it in con_img
        if len(it.get("title", "")) >= 30 and not FLUFF.search(it["title"])
    ]
    # con imagen pero cortas: sirven de relleno, nunca las descartadas por relleno
    resto = [
        it for it in con_img
        if it not in utiles and not FLUFF.search(it["title"])
    ]
    relleno = [it for it in con_img if it not in utiles and it not in resto]
    sin_img = [it for it in items if not it.get("image")]

    utiles.sort(key=peso, reverse=True)
    resto.sort(key=peso, reverse=True)
    relleno.sort(key=peso, reverse=True)
    sin_img.sort(key=peso, reverse=True)

    picked, used = [], set()
    for grupo in (utiles, resto):
        for it in grupo:
            if len(picked) == n:
                return picked
            sec = it["tags"][0] if it.get("tags") else "industria"
            if sec in used:
                continue
            picked.append(it)
            used.add(sec)
        if len(picked) == n:
            return picked
        for it in grupo:            # repetir sección antes que quedarse sin foto
            if len(picked) >= n:
                return picked
            if it not in picked:
                picked.append(it)
    for it in sin_img + relleno:    # último recurso
        if len(picked) >= n:
            break
        if it not in picked:
            picked.append(it)
    return picked[:n]


# --------------------------------------------------------------------------- guion

PROMPT = """Eres editor de un noticiero diario sobre {enfoque}, para redes sociales.

Hoy es {fecha}. Estas son las noticias seleccionadas:

{noticias}

Escribe el guion de una capsula vertical de 55 segundos, en espanol neutro, tono informativo y agil.
Reglas:
- "hook": una sola frase de gancho, maximo 14 palabras, que resuma lo mas importante del dia.
- "segments": un objeto por noticia, en el mismo orden, con:
   - "n": numero de la noticia
   - "text": la voz en off explica la noticia en DOS frases y entre 22 y 32 palabras:
     que ha pasado y por que importa. No copies el titular ni lo empieces con "Segun".
   - "titular": texto corto para pantalla, maximo 7 palabras, sin punto final
- "outro": una frase de cierre, maximo 10 palabras.
- Todo en espanol: traduce marcas de productos si hace falta explicarlas, pero deja los
  nombres propios (Chanel, Kering, Balenciaga) como estan.
- No inventes cifras ni datos que no aparezcan en las noticias.
{extra}- No uses comillas ni asteriscos.
Devuelve SOLO el JSON, sin explicaciones."""


def build_prompt(items, fecha):
    lines = []
    for i, it in enumerate(items, 1):
        sec = SECTION_LABEL.get(it["tags"][0] if it.get("tags") else "", "")
        lines.append(f"{i}. [{it['source']} | {sec}] {it['title']}")
        if it.get("excerpt"):
            lines.append(f"   {it['excerpt'][:220]}")
    return PROMPT.format(fecha=fecha, noticias="\n".join(lines), enfoque=ED["enfoque"], extra=ED["extra"])


def llm_script(items, fecha):
    key = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        return None, "sin clave API"
    base = (os.environ.get("LLM_BASE_URL") or "https://api.deepseek.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL") or "deepseek-chat"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": build_prompt(items, fecha)}],
        "temperature": 0.6,
        "response_format": {"type": "json_object"},
    }
    for intento in (1, 2):
        try:
            req = urllib.request.Request(
                base + "/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
            txt = data["choices"][0]["message"]["content"].strip()
            txt = re.sub(r"^```(?:json)?|```$", "", txt, flags=re.M).strip()
            script = json.loads(txt)
            if script.get("hook") and script.get("segments"):
                return script, f"IA ({model})"
        except Exception as exc:  # noqa: BLE001
            if intento == 2:
                return None, f"fallo IA: {type(exc).__name__}"
            body.pop("response_format", None)
    return None, "fallo IA"


def first_sentence(text, minlen=40, maxlen=190):
    """Primera frase útil: ignora abreviaturas tipo 'Dr.' y no se pasa de largo."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    if len(text) <= maxlen:
        return text
    corte = text.find(". ", minlen)
    frase = text[: corte + 1] if corte != -1 else text[:maxlen]
    if len(frase) > maxlen:
        coma = frase.rfind(", ", 0, maxlen)
        frase = frase[: coma + 1] if coma > 80 else frase[:maxlen].rsplit(" ", 1)[0] + "."
    return frase.strip()


def clip_words(text, n):
    """Recorta a n palabras sin dejar la frase colgando de una coma o un 'de'."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    words = text.split(" ")
    if len(words) <= n:
        return text
    cut = words[:n]
    while len(cut) > 6 and cut[-1].lower().strip(",.;:") in TRAILING:
        cut.pop()
    frase = " ".join(cut).rstrip(",;:. ")
    # si hay una coma cerca del final, cortar ahí deja una frase completa
    coma = frase.rfind(", ")
    if coma > len(frase) * 0.55:
        frase = frase[:coma]
    return frase + "."


def template_script(items):
    """Sin IA: traduce al español y arma un resumen con titular + entradilla."""
    segs = []
    for i, it in enumerate(items, 1):
        es = it.get("lang") == "es"  # ya viene en español: no gastar traducciones
        titulo_es = it["title"] if es else (translate_es(it["title"]) or it["title"])
        resumen = it.get("excerpt") or page_description(it["link"])
        frase = ""
        if resumen:
            primera = first_sentence(resumen)
            if primera and len(primera) > 20:
                frase = clip_words(primera if es else translate_es(primera), 18)
        texto = f"{titulo_es.rstrip(' .')}. {frase}".strip()
        segs.append({"n": i, "text": texto, "titular": short_title(titulo_es)})
    return {"hook": ED["hook"], "segments": segs, "outro": ED["outro"]}


def normalise_script(script, items):
    """Asegura que hay un segmento por noticia y que los textos son pronunciables."""
    segs = script.get("segments") or []
    by_n = {}
    for s in segs:
        try:
            by_n[int(s.get("n"))] = s
        except Exception:  # noqa: BLE001
            continue
    out = []
    for i, it in enumerate(items, 1):
        s = by_n.get(i) or {}
        text = (s.get("text") or "").strip()
        titular = (s.get("titular") or "").strip() or short_title(it["title"])
        if not text:
            text = it["title"]
        out.append({"n": i, "text": text, "titular": titular, "item": it})
    return {
        "hook": (script.get("hook") or "Hoy en la industria de la moda.").strip(),
        "segments": out,
        "outro": (script.get("outro") or "Mañana, más moda.").strip(),
    }


# --------------------------------------------------------------------------- voz

def synth_edge(text, path):
    import edge_tts  # import perezoso: solo si se usa

    async def _go():
        comm = edge_tts.Communicate(text, VOICE, rate=RATE)
        await comm.save(str(path))

    asyncio.run(_go())


def synth(text, path, mode):
    """Genera el audio de una frase. mode: edge | silent."""
    words = max(1, len(text.split()))
    if mode == "silent":
        secs = round(words / 2.7 + 0.5, 2)
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
             "-i", "anullsrc=r=48000:cl=stereo", "-t", str(secs),
             "-c:a", "libmp3lame", "-b:a", "96k", str(path)])
        return
    synth_edge(text, path)


# --------------------------------------------------------------------------- imágenes

def download_image(url, dest, max_bytes=12 * 1024 * 1024):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
        with urllib.request.urlopen(req, timeout=25) as r:
            data = r.read(max_bytes + 1)
        if len(data) > max_bytes or len(data) < 3000:
            return None
        dest.write_bytes(data)
        return dest
    except Exception:  # noqa: BLE001
        return None


PALETTE = [
    ("#1b1030", "#ff4d6d"), ("#101a2b", "#4da3ff"), ("#1a2410", "#c9ff4a"),
    ("#241016", "#ff9f4d"), ("#101f1f", "#4dffd2"), ("#221022", "#d24dff"),
]


def gradient_canvas(text, seed, monograma=True):
    """Fondo de marca para noticias sin imagen usable."""
    c1, c2 = PALETTE[int(hashlib.sha1(seed.encode("utf-8")).hexdigest(), 16) % len(PALETTE)]
    img = Image.new("RGB", (ZOOM_W, ZOOM_H), c1)
    d = ImageDraw.Draw(img)

    def rgb(hx):
        hx = hx.lstrip("#")
        return tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))

    a, b = rgb(c1), rgb(c2)
    for y in range(ZOOM_H):
        t = y / ZOOM_H
        col = tuple(int(a[i] + (b[i] - a[i]) * t * 0.55) for i in range(3))
        d.line([(0, y), (ZOOM_W, y)], fill=col)
    if monograma:
        # inicial discreta, arriba a la derecha, para que no compita con el titular
        letras = "".join(w[0] for w in text.split()[:2]).upper() or "M"
        f = load_font(300, bold=True)
        capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(capa).text((ZOOM_W - 120, 320), letras, font=f,
                                  fill=(255, 255, 255, 26), anchor="rm")
        img = Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")
    return img


# --------------------------------------------------------------------------- foto relacionada
#
# Cuando la noticia no trae foto usable (p. ej. notas de Google News cuyo enlace no se
# pudo resolver) se busca una foto con licencia libre en Openverse (Flickr, Wikimedia...)
# por lugar y tema, y se muestra el crédito del fotógrafo en la diapositiva.

OPENVERSE = "https://api.openverse.org/v1/images/"
_OV_CACHE = {}

LUGARES = [
    (r"tijuana", "Tijuana"), (r"baja california|ensenada|mexicali|rosarito", "Baja California"),
    (r"cdmx|ciudad de m[eé]xico|polanco", "Mexico City"), (r"guadalajara", "Guadalajara"),
    (r"monterrey", "Monterrey"), (r"colombia|bogot[aá]|medell[ií]n", "Colombia"),
    (r"argentin|buenos aires", "Buenos Aires"), (r"per[uú]\b|lima\b", "Peru"),
    (r"m[eé]xic", "Mexico"),
]
TEMAS = [
    (r"catrina|d[ií]a de muertos", "catrina"),
    (r"pasarela|desfile|fashion week|runway|semana de la moda|fashion show", "fashion show runway"),
    (r"zapato|tenis|calzado|sneaker|shoe|bota", "shoes"),
    (r"joy|jewel|reloj|watch", "jewelry"),
    (r"belleza|maquillaje|cosm[eé]tic|perfum|beauty|makeup", "makeup"),
    (r"textil|fabric|tela|hilo", "textile fabric"),
    (r"tienda|boutique|store|retail|centro comercial|mall|almac[eé]n", "boutique shop"),
    (r"dise[nñ]ador|colecci[oó]n|designer|collection", "fashion designer"),
]
TEMA_SECCION = {
    "pasarela": "fashion show runway", "diseno": "fashion designer", "retail": "boutique shop",
    "belleza": "makeup", "calzado": "shoes", "negocio": "fashion store", "sostenibilidad": "textile",
}


def related_queries(item):
    extracto = item.get("excerpt", "")
    if extracto.startswith("Publicado por"):
        extracto = ""  # es el nombre del medio, no habla de la noticia
    texto = f"{item.get('title', '')} {extracto}"
    lugar = next((n for rx, n in LUGARES if re.search(rx, texto, re.I)), "")
    if not lugar and item.get("source") == "Tijuana":
        lugar = "Tijuana"  # la búsqueda "Moda en Tijuana" ya es de la ciudad
    tema = next((n for rx, n in TEMAS if re.search(rx, texto, re.I)), "")
    sec = item["tags"][0] if item.get("tags") else ""
    tema = tema or TEMA_SECCION.get(sec, "fashion")
    qs = []
    if lugar:
        qs += [f"{tema} {lugar}", f"fashion {lugar}"]
    qs += [tema, "fashion"]
    return list(dict.fromkeys(qs))


def openverse(q):
    if q in _OV_CACHE:
        return _OV_CACHE[q]
    url = OPENVERSE + "?" + urllib.parse.urlencode({"q": q, "page_size": 20, "mature": "false"})
    res = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            res = json.loads(r.read().decode("utf-8")).get("results") or []
    except Exception as exc:  # noqa: BLE001
        print(f"  ! Openverse ({q}): {type(exc).__name__}")
    _OV_CACHE[q] = res
    return res


def credit_line(r):
    autor = (r.get("creator") or r.get("provider") or "").strip()
    lic = (r.get("license") or "").lower()
    ver = (r.get("license_version") or "").strip()
    if lic == "cc0":
        lic_txt = "CC0"
    elif lic == "pdm":
        lic_txt = "dominio público"
    elif lic:
        lic_txt = f"CC {lic.upper()} {ver}".strip()
    else:
        lic_txt = ""
    txt = "Foto: " + " · ".join(x for x in (autor, lic_txt) if x)
    return txt if len(txt) <= 70 else txt[:67].rstrip() + "…"


def related_photo(item, workdir, idx, used):
    """Busca una foto relacionada con licencia libre. Devuelve (imagen, crédito)."""
    for q in related_queries(item):
        for r in openverse(q):
            url = r.get("url")
            if not url or url in used:
                continue
            if min(r.get("width") or 0, r.get("height") or 0) < 700:
                continue
            img = _load_image(url, workdir, f"{idx}rel")
            if img and min(img.size) >= 600:
                used.add(url)
                print(f"  foto relacionada para '{item['title'][:50]}' ({q}): {credit_line(r)}")
                return img, credit_line(r)
    return None, None


WP_THUMB = re.compile(r"-\d{2,4}x\d{2,4}(\.[a-z]{3,4})(?:\?.*)?$", re.I)


def _load_image(url, workdir, idx):
    if not url:
        return None
    dest = workdir / f"src{idx}.img"
    if not download_image(url, dest):
        return None
    try:
        img = Image.open(dest)
        return ImageOps.exif_transpose(img).convert("RGB")
    except Exception:  # noqa: BLE001
        return None


def _cover(img):
    ratio = ZOOM_W / ZOOM_H
    w, h = img.size
    if w / h > ratio:
        new_w = int(h * ratio)
        img = img.crop(((w - new_w) // 2, 0, (w + new_w) // 2, h))
    else:
        new_h = int(w / ratio)
        top = max(0, (h - new_h) // 2)
        img = img.crop((0, top, w, top + new_h))
    return img.resize((ZOOM_W, ZOOM_H), Image.LANCZOS)


def prepare_photo(item, workdir, idx, used=None):
    """Foto de la noticia. Cadena: RSS → original sin sufijo → og:image →
    foto relacionada con licencia libre (Openverse) → desenfoque → fondo de marca.
    Si usa una foto relacionada deja su crédito en item["_credito"]."""
    used = set() if used is None else used
    candidatos = []
    if item.get("image"):
        candidatos.append(item["image"])
        m = WP_THUMB.search(item["image"])
        if m:  # WordPress suele dar "foto-150x150.jpg"; la original es "foto.jpg"
            candidatos.append(WP_THUMB.sub(m.group(1), item["image"]))

    buena, pequena = None, None
    for url in candidatos:
        img = _load_image(url, workdir, idx)
        if not img:
            continue
        if min(img.size) >= 420:
            buena = img
            break
        pequena = pequena or img

    if buena is None:
        og = og_image(item["link"])
        img = _load_image(og, workdir, idx)
        if img and min(img.size) >= 420:
            buena = img
        elif img:
            pequena = pequena or img

    if buena is None:
        buena, credito = related_photo(item, workdir, idx, used)
        if buena is not None:
            item["_credito"] = credito

    path = workdir / f"photo{idx}.jpg"
    if buena is not None:
        _cover(buena).save(path, quality=92, subsampling=1)
        return path, True

    if pequena is not None:
        # sin foto grande: se usa como fondo abstracto, mucho mejor que un hueco
        fondo = _cover(pequena).filter(ImageFilter.GaussianBlur(26))
        fondo = Image.eval(fondo, lambda v: int(v * 0.55))
        fondo.save(path, quality=90)
        return path, False

    gradient_canvas(item["source"], item["link"]).save(path, quality=90)
    return path, False


def make_overlay(titular, section, source, out_path, kicker=None, big=False, raw_footer=False, credit=None):
    """Capa transparente con el texto fijo de la diapositiva."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # una sola rampa de opacidad por fila: velo + sombra arriba + degradado abajo.
    # (ImageDraw reemplaza el alfa, no lo mezcla: dibujar capas separadas deja bandas)
    top = int(H * 0.34)
    for y in range(H):
        a = 55
        if y < 320:
            a = max(a, int(150 * (1 - y / 320) ** 1.4))
        if y >= top:
            t = (y - top) / (H - top)
            a = max(a, int(252 * min(1.0, t ** 1.55)))
        d.line([(0, y), (W, y)], fill=(6, 6, 8, a))

    # marca arriba
    f_marca = load_font(38, bold=True)
    d.text((64, 84), "MODA", font=f_marca, fill=(255, 255, 255, 232))
    wm = d.textlength("MODA", font=f_marca)
    d.text((64 + wm + 4, 84), "/", font=f_marca, fill=ACCENT + (255,))
    d.text((64 + wm + 24, 84), "RADAR", font=f_marca, fill=(255, 255, 255, 150))
    if ED["tag"]:
        wr = d.textlength("RADAR", font=f_marca)
        f_tag = load_font(26, bold=True)
        d.text((64 + wm + 24 + wr + 22, 92), ED["tag"], font=f_tag, fill=ACCENT + (255,))

    y = int(H * 0.60)
    if kicker:
        f_k = load_font(30, bold=True)
        x = 66
        for ch in kicker.upper():  # espaciado según el ancho real de cada letra
            d.text((x, y), ch, font=f_k, fill=ACCENT + (255,))
            x += d.textlength(ch, font=f_k) + 7
        y += 62

    if section:
        f_s = load_font(34, bold=True)
        d.text((66, y), section.upper(), font=f_s, fill=(255, 255, 255, 165))
        y += 58

    max_w = W - 132
    font, lines = fit_headline(d, titular, max_w, 4 if not big else 3)
    line_h = int(font.size * 1.16)
    y += 14
    for line in lines:
        d.text((69, y + 5), line, font=font, fill=(0, 0, 0, 130))
        d.text((66, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_h

    if source:
        f_src = load_font(30, bold=False)
        texto = source if raw_footer else f"Fuente: {source}"
        d.text((66, H - 168), texto, font=f_src, fill=(255, 255, 255, 130))
    if credit:
        f_cr = load_font(24, bold=False)
        d.text((66, H - 122), credit, font=f_cr, fill=(255, 255, 255, 115))

    img.save(out_path)
    return out_path


def make_brand_overlay(out_path, meta_line=None):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(6, 6, 8, int(120 + 110 * t)))

    f = load_font(112, bold=True)
    wm = d.textlength("MODA", font=f)
    ws = d.textlength("/", font=f)
    wr = d.textlength("RADAR", font=f)
    x = (W - (wm + ws + wr)) / 2
    y0 = H / 2 - 150
    d.text((x, y0), "MODA", font=f, fill=(255, 255, 255, 240))
    d.text((x + wm, y0), "/", font=f, fill=ACCENT + (255,))
    d.text((x + wm + ws, y0), "RADAR", font=f, fill=(255, 255, 255, 240))

    f2 = load_font(44, bold=False)
    txt = meta_line or "Mañana, más moda."
    d.text(((W - d.textlength(txt, font=f2)) / 2, y0 + 190), txt, font=f2,
           fill=(235, 233, 228, 210))
    img.save(out_path)
    return out_path


# --------------------------------------------------------------------------- montaje

def render_slide(photo, overlay, audio, out_path, dur, reverse=False):
    """Foto con paneo lento + texto fijo + audio, sin recodificar el color."""
    d = max(0.6, dur)
    if reverse:
        x = f"(iw-ow)*(1-min(t/{d:.3f},1))"
    else:
        x = f"(iw-ow)*min(t/{d:.3f},1)"
    filt = (
        f"[0:v]scale={ZOOM_W}:{ZOOM_H}:force_original_aspect_ratio=increase,"
        f"crop={ZOOM_W}:{ZOOM_H},"
        f"crop={W}:{H}:x='{x}':y='(ih-oh)/2',fps={FPS},format=yuv420p[v];"
        f"[v][1:v]overlay=0:0:format=auto[vv];"
        f"[2:a]apad=pad_dur=0.30[a]"
    )
    run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-t", f"{d:.3f}", "-i", str(photo),
        "-loop", "1", "-t", f"{d:.3f}", "-i", str(overlay),
        "-i", str(audio),
        "-filter_complex", filt,
        "-map", "[vv]", "-map", "[a]",
        "-t", f"{d:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        str(out_path),
    ])


def concat_slides(slides, out_path, workdir):
    lista = workdir / "lista.txt"
    lista.write_text(
        "".join(f"file '{s.as_posix()}'\n" for s in slides), encoding="utf-8"
    )
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
        "-i", str(lista), "-c", "copy", "-movflags", "+faststart", str(out_path),
    ])


def normalize_loudness(path, workdir, target=-17.0):
    """Sube el volumen al nivel de redes sociales; en el móvil se entiende mucho mejor."""
    try:
        p = subprocess.run(
            ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True,
        )
        m = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", p.stderr)
        if not m:
            return 0.0
        ganancia = max(0.0, min(9.0, target - float(m.group(1))))
        if ganancia < 0.5:
            return 0.0
        tmp = workdir / "norm.mp4"
        run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-c:v", "copy",
            "-af", f"volume={ganancia:.1f}dB,alimiter=limit=0.89",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", str(tmp),
        ])
        shutil.move(str(tmp), str(path))
        return ganancia
    except Exception:  # noqa: BLE001
        return 0.0


def music_track(root, pedido=None):
    """Pista de fondo: --music, o musica/fondo.mp3, o el primer mp3 de musica/."""
    if pedido:
        p = root / pedido
        return p if p.exists() else None
    d = root / "musica"
    if not d.is_dir():
        return None
    default = d / "fondo.mp3"
    if default.exists():
        return default
    mp3s = sorted(d.glob("*.mp3"))
    return mp3s[0] if mp3s else None


def music_gain(music, target=-30.0):
    """Ganancia para dejar la música ~14 dB por debajo de la voz."""
    try:
        p = subprocess.run(
            ["ffmpeg", "-i", str(music), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True,
        )
        m = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", p.stderr)
        if not m:
            return 0.0
        return max(-30.0, min(24.0, target - float(m.group(1))))
    except Exception:  # noqa: BLE001
        return 0.0


def add_music(video, music, workdir, dur):
    """Mezcla la música en bucle, con entrada y salida suaves, sin tapar la voz."""
    gain = music_gain(music)
    salida = max(1.0, dur - 3.0)
    filt = (
        f"[1:a]volume={gain:.1f}dB,afade=t=in:st=0:d=2,"
        f"afade=t=out:st={salida:.2f}:d=3[m];"
        f"[0:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]"
    )
    tmp = workdir / "con_musica.mp4"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
        "-stream_loop", "-1", "-i", str(music),
        "-filter_complex", filt,
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-shortest", str(tmp),
    ])
    shutil.move(str(tmp), str(video))
    return gain


def cover_frame(video, out_path):
    try:
        dur = ffprobe_duration(video)
        t = min(max(1.0, dur * 0.12), 4.0)
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}",
             "-i", str(video), "-frames:v", "1", "-q:v", "3", str(out_path)])
        return out_path
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- principal

def main(argv=None):
    ap = argparse.ArgumentParser(description="Genera la cápsula diaria en vídeo.")
    ap.add_argument("--edition", default="docs/data/latest.json", help="JSON de la edición")
    ap.add_argument("--out", default="docs/videos", help="carpeta de salida")
    ap.add_argument("--items", type=int, default=MAX_ITEMS, help="noticias en la cápsula")
    ap.add_argument("--tts", choices=["edge", "silent"], default="edge", help="motor de voz")
    ap.add_argument("--no-llm", action="store_true", help="forzar la plantilla sin IA")
    ap.add_argument("--no-trad", action="store_true", help="no traducir (para depurar la plantilla)")
    ap.add_argument("--music", default=None, help="pista de fondo (por defecto musica/fondo.mp3)")
    ap.add_argument("--sin-musica", action="store_true", help="no mezclar música")
    ap.add_argument("--dry-run", action="store_true", help="solo mostrar el guion")
    ap.add_argument("--keep", type=int, default=KEEP_VIDEOS, help="vídeos a conservar")
    ap.add_argument("--workdir", default=".tmp", help="carpeta de trabajo (se borra al final)")
    ap.add_argument("--edicion", choices=sorted(EDICIONES), default="general",
                    help="general (todas las noticias) o latam (México y Latinoamérica)")
    args = ap.parse_args(argv)
    global ED
    ED = EDICIONES[args.edicion]

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

    root = Path(__file__).resolve().parent
    ed_path = root / args.edition
    if not ed_path.exists():
        print(f"No existe la edicion {ed_path}. Ejecuta antes aggregate.py.")
        return 1
    edition = json.loads(ed_path.read_text(encoding="utf-8"))
    items = edition.get("items") or []
    if ED["filtro"]:
        items = [it for it in items if ED["filtro"](it)]
        print(f"edicion {args.edicion}: {len(items)} noticias candidatas")
        if len(items) < 3:
            # dia flojo en la region: no es un error, simplemente hoy no hay capsula
            print("Hoy no hay noticias suficientes de la region para la capsula.")
            return 0
    if len(items) < 3:
        print("Muy pocas noticias para montar la capsula.")
        return 1

    # las noticias sin foto en el RSS suelen tenerla en la página: la buscamos antes de elegir
    con_foto = resolve_images(items)
    print(f"imagenes resueltas: {con_foto}/{len(items)}")
    picked = pick_items(items, args.items, ED["bonus"])
    if ED.get("prioridad"):
        picked = reserve_priority(picked, items, ED["prioridad"], ED["prioridad_max"])
    # la fecha es la de la edición, no la del reloj: si se monta a mano después de
    # medianoche UTC (las 4 pm en Tijuana) el panel no encontraría el vídeo
    fecha = (edition.get("generated") or "")[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    script, origen = (None, "plantilla") if args.no_llm else llm_script(picked, fecha)
    if script is None:
        script, origen = template_script(picked), f"plantilla ({origen})"
    script = normalise_script(script, picked)

    print(f"Capsula {args.edicion} {fecha} · {len(picked)} noticias · guion: {origen}")
    print(f"  gancho: {script['hook']}")
    for s in script["segments"]:
        print(f"  {s['n']}. [{s['item']['source']}] {s['titular']}")
        print(f"     voz: {s['text']}")
    print(f"  cierre: {script['outro']}")

    if args.dry_run:
        return 0

    outdir = root / args.out
    outdir.mkdir(parents=True, exist_ok=True)
    final = outdir / f"{fecha}{ED['sufijo']}.mp4"

    work = root / args.workdir / f"capsula-{os.getpid()}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        # 1. voz
        audios = []
        tareas = [("hook", script["hook"])] + [
            (f"seg{s['n']}", s["text"]) for s in script["segments"]
        ] + [("outro", script["outro"])]
        for name, texto in tareas:
            p = work / f"{name}.mp3"
            synth(texto, p, args.tts)
            audios.append((name, p, ffprobe_duration(p)))

        # 2. diapositivas
        slides = []
        # gancho: imagen de la noticia principal
        ph = datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
        lead = picked[0]
        usadas = set()  # fotos relacionadas ya usadas: no repetir la misma en dos diapositivas
        photo, _ = prepare_photo(lead, work, 0, usadas)
        ov = make_overlay(ED["portada"], "", ph,
                          work / "ov_hook.png", kicker=ED["kicker"], big=True, raw_footer=True)
        s_hook = work / "s_hook.mp4"
        dur = audios[0][2] + 0.35
        render_slide(photo, ov, audios[0][1], s_hook, dur)
        slides.append(s_hook)

        # 3. una por noticia
        for i, seg in enumerate(script["segments"], 1):
            it = seg["item"]
            photo, _ = prepare_photo(it, work, i, usadas)
            sec = SECTION_LABEL.get(it["tags"][0] if it.get("tags") else "", "")
            fuente = it.get("via") or it["source"]  # en Google News por tema, el medio real
            ov = make_overlay(seg["titular"], sec, fuente, work / f"ov{i}.png",
                              credit=it.get("_credito"))
            name, ap_path, adur = audios[i]
            s = work / f"s{i}.mp4"
            render_slide(photo, ov, ap_path, s, adur + 0.35, reverse=(i % 2 == 0))
            slides.append(s)

        # 4. cierre
        fund = gradient_canvas("Moda Radar", f"cierre{fecha}{ED['sufijo']}", monograma=False)
        cp = work / "cierre.jpg"
        fund.save(cp, quality=92)
        ov = make_brand_overlay(work / "ov_outro.png", ED["cierre"].format(fecha=ph))
        s_out = work / "s_outro.mp4"
        render_slide(cp, ov, audios[-1][1], s_out, audios[-1][2] + 0.6)
        slides.append(s_out)

        # 5. unir
        concat_slides(slides, final, work)
        ganancia = normalize_loudness(final, work)
        total = ffprobe_duration(final)

        # 6. música de fondo
        musi = None if args.sin_musica else music_track(root, args.music)
        g_mus = 0.0
        if musi:
            g_mus = add_music(final, musi, work, ffprobe_duration(final))
        cover = cover_frame(final, outdir / f"{fecha}{ED['sufijo']}-portada.jpg")

        # 6. rotación
        patron = re.compile(r"^\d{4}-\d{2}-\d{2}" + re.escape(ED["sufijo"]) + r"\.mp4$")
        viejos = sorted(v for v in outdir.glob("*.mp4") if patron.match(v.name))
        for old in viejos[:-args.keep]:
            old.unlink(missing_ok=True)
            (outdir / (old.stem + "-portada.jpg")).unlink(missing_ok=True)

        meta = {
            "date": fecha,
            "edition": args.edicion,
            "duration": round(total, 1),
            "script_source": origen,
            "hook": script["hook"],
            "items": [
                {"title": s["titular"], "source": s["item"].get("via") or s["item"]["source"],
                 "link": s["item"]["link"], "photo_credit": s["item"].get("_credito")}
                for s in script["segments"]
            ],
        }
        (outdir / f"index{ED['sufijo']}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
        )

        size_mb = final.stat().st_size / 1024 / 1024
        print(f"\nListo: {final.relative_to(root)} · {total:.1f}s · {size_mb:.1f} MB")
        if ganancia:
            print(f"Audio normalizado: +{ganancia:.1f} dB")
        if musi:
            print(f"Musica: {musi.name} ({g_mus:+.1f} dB)")
        if cover:
            print(f"Portada: {cover.relative_to(root)}")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
