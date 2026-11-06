"""Resuelve los enlaces de Google News al artículo real.

Los feeds de Google News (los espejos de BoF, Modaes, FashionNetwork y las búsquedas por
tema como "Moda en Tijuana") dan enlaces del tipo news.google.com/rss/articles/CBMi...
Son redirecciones opacas: no llevan al artículo sin JavaScript, caducan y su página es
de Google, así que de ahí no sale ni foto ni entradilla.

Este módulo:
  1. descifra el id del enlace con el mismo servicio que usa la web de Google News
     (dos peticiones: la página del artículo da una firma, batchexecute da la URL);
  2. abre el artículo real y lee su og:image y su og:description;
  3. guarda el resultado en datos/enlaces-cache.json para no repetir peticiones.

Solo biblioteca estándar. Si Google cambia el mecanismo, todo falla en silencio y la
noticia se queda como estaba (enlace de Google, sin foto): el radar no se rompe.
"""

from __future__ import annotations

import base64
import concurrent.futures as cf
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT = 15
MAX_CACHE = 1500

ID_RX = re.compile(r"news\.google\.[a-z.]+/(?:rss/)?articles/([A-Za-z0-9_-]+)")
SG_RX = re.compile(r'data-n-a-sg="([^"]+)"')
TS_RX = re.compile(r'data-n-a-ts="([^"]+)"')
RES_RX = re.compile(r'garturlres\\",\\"(https?://[^"\\]+)')
META_RX = {
    "image": re.compile(
        r"""<meta[^>]+(?:property|name)\s*=\s*["'](?:og:image|twitter:image)(?::src)?["']"""
        r"""[^>]+content\s*=\s*["']([^"']+)["']""", re.I),
    "image2": re.compile(
        r"""<meta[^>]+content\s*=\s*["']([^"']+)["'][^>]+(?:property|name)\s*=\s*["']"""
        r"""(?:og:image|twitter:image)["']""", re.I),
    "desc": re.compile(
        r"""<meta[^>]+(?:property|name)\s*=\s*["'](?:og:description|description)["']"""
        r"""[^>]+content\s*=\s*["']([^"']+)["']""", re.I),
    "desc2": re.compile(
        r"""<meta[^>]+content\s*=\s*["']([^"']+)["'][^>]+(?:property|name)\s*=\s*["']"""
        r"""(?:og:description|description)["']""", re.I),
}


def es_google(link):
    return bool(ID_RX.search(link or ""))


def _get(url, data=None, headers=None, limit=700_000):
    h = {"User-Agent": UA, "Accept-Language": "es-MX,es;q=0.9,en;q=0.8"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read(limit).decode("utf-8", "ignore"), r.geturl()


def _from_base64(art_id):
    """Formato antiguo: el id es base64 y lleva la URL dentro."""
    try:
        raw = base64.urlsafe_b64decode(art_id + "=" * (-len(art_id) % 4))
    except Exception:  # noqa: BLE001
        return None
    m = re.search(rb"https?://[\x21-\x7e]+", raw)
    if not m:
        return None
    url = m.group(0).decode("ascii", "ignore")
    # el id termina en bytes de control: se corta en lo que no es URL
    url = re.split(r"[\x00-\x20\"<>]", url)[0]
    return url if "news.google." not in url else None


def decode(link):
    """URL real de un enlace de Google News, o None."""
    m = ID_RX.search(link or "")
    if not m:
        return None
    art_id = m.group(1)
    if not art_id.startswith("AU_yqL"):
        url = _from_base64(art_id)
        if url:
            return url
    sg = ts = None
    for base in ("https://news.google.com/articles/", "https://news.google.com/rss/articles/"):
        try:
            page, _ = _get(base + art_id)
        except Exception:  # noqa: BLE001
            continue
        a, b = SG_RX.search(page), TS_RX.search(page)
        if a and b:
            sg, ts = a.group(1), b.group(1)
            break
    if not sg:
        return None
    inner = (
        '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,'
        'null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
        f'"{art_id}",{ts},"{sg}"]'
    )
    body = "f.req=" + urllib.parse.quote(json.dumps([[["Fbv4je", inner, None, "generic"]]]))
    try:
        txt, _ = _get(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
    except Exception:  # noqa: BLE001
        return None
    try:
        parts = json.loads(txt.split("\n\n", 1)[1])
        for row in parts:
            if isinstance(row, list) and len(row) > 2 and isinstance(row[2], str) and "garturlres" in row[2]:
                url = json.loads(row[2])[1]
                if isinstance(url, str) and url.startswith("http"):
                    return url
    except Exception:  # noqa: BLE001
        pass
    m = RES_RX.search(txt)
    return m.group(1) if m else None


def article_meta(url):
    """(imagen, descripción) del artículo; cadenas vacías si no hay."""
    try:
        page, final = _get(url)
    except Exception:  # noqa: BLE001
        return "", ""
    head = page[:300_000]

    def grab(*keys):
        for k in keys:
            m = META_RX[k].search(head)
            if m:
                return html.unescape(m.group(1)).strip()
        return ""

    img = grab("image", "image2")
    if img and not img.startswith("http"):
        img = urllib.parse.urljoin(final, img)
    desc = re.sub(r"\s+", " ", grab("desc", "desc2"))
    return img, desc


def _resolve_one(link):
    url = decode(link)
    if not url:
        return {"url": None, "t": int(time.time())}
    img, desc = article_meta(url)
    return {"url": url, "image": img, "desc": desc, "t": int(time.time())}


def load_cache(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def save_cache(path, cache):
    # se conservan las más recientes; los fallos se reintentan pasados 2 días
    items = sorted(cache.items(), key=lambda kv: kv[1].get("t", 0), reverse=True)[:MAX_CACHE]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(dict(items), ensure_ascii=False, indent=0), encoding="utf-8")


def resolve(links, cache, limit=40, workers=4):
    """Resuelve hasta `limit` enlaces nuevos (en orden de prioridad). Devuelve
    {enlace_google: info} para todos los que estén en caché o se hayan resuelto."""
    ahora = int(time.time())
    pendientes = []
    for link in links:
        info = cache.get(link)
        if info and (info.get("url") or ahora - info.get("t", 0) < 2 * 86400):
            continue
        if link not in pendientes:
            pendientes.append(link)
    pendientes = pendientes[:limit]
    if pendientes:
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for link, info in zip(pendientes, ex.map(_resolve_one, pendientes)):
                cache[link] = info
    return {lk: cache[lk] for lk in links if lk in cache}
