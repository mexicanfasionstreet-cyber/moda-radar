#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""moda-radar — radar diario de noticias de la industria de la moda.

Qué hace:
  1. Descarga los RSS/Atom de las fuentes de sources.json (en paralelo).
  2. Limpia, normaliza y descarta noticias fuera de la ventana de días.
  3. Elimina duplicados entre medios (misma noticia en BoF y WWD = una sola).
  4. Clasifica cada noticia en secciones (negocio, retail, pasarela, sostenibilidad...).
  5. Genera el panel HTML (docs/index.html), los datos JSON (docs/data/) y el digest Markdown (digests/).

Solo usa la biblioteca estándar de Python 3.9+. Sin claves API. Sin coste.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import gzip
import hashlib
import html
import json
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import ui

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
MAX_PER_FEED = 15
TIMEOUT = 30

CATS = [
    {
        "slug": "negocio",
        "label": "Negocio",
        "kw": [
            "revenue", "sales", "earnings", "profit", "loss", "quarter", "quarterly", "fiscal",
            "ipo", "listing", "acquisition", "acquires", "acquired", "merger", "stake", "valuation",
            "funding", "investor", "investment", "buyout", "bankruptcy", "insolvency", "administration",
            "turnover", "margin", "forecast", "outlook", "conglomerate", "shares", "stock", "growth",
            "licensing", "franchise", "joint venture", "partnership", "deal", "billion", "million",
            "ingresos", "ventas", "beneficio", "resultados", "facturacion", "compra", "adquisicion",
            "fusion", "inversion", "billon", "millones", "crecimiento", "bilancio", "fatturato", "utile",
        ],
    },
    {
        "slug": "retail",
        "label": "Retail",
        "kw": [
            "store", "stores", "opening", "opens", "closure", "closes", "closing", "flagship", "boutique",
            "pop-up", "popup", "e-commerce", "ecommerce", "wholesale", "marketplace", "dtc", "direct-to-consumer",
            "footfall", "black friday", "cyber monday", "outlet", "mall", "department store",
            "shopper", "shoppers", "retail", "retailer", "online sales",
            "tienda", "tiendas", "apertura", "cierre", "comercio", "minorista", "venta online", "negocio online",
            "negozio", "boutique", "vendite online",
        ],
    },
    {
        "slug": "pasarela",
        "label": "Pasarela",
        "kw": [
            "runway", "catwalk", "fashion week", "couture", "ready-to-wear",
            "lookbook", "campaign", "debut", "backstage",
            "front row", "menswear", "womenswear", "resort", "pre-fall",
            "pasarela", "desfile", "desfiles", "coleccion", "temporada", "semana de la moda", "modelo",
            "sfilata", "collezione", "settimana della moda",
        ],
    },
    {
        "slug": "sostenibilidad",
        "label": "Sostenibilidad",
        "kw": [
            "sustainability", "sustainable", "circular", "circularity", "recycled", "recycling", "upcycled",
            "emissions", "carbon", "esg", "supply chain", "supplier", "suppliers", "factory", "factories",
            "workers", "labour", "labor", "wage", "wages", "garment worker", "textile waste", "resale",
            "second-hand", "resale", "vegan", "leather-free", "fur-free", "transparency", "traceability",
            "greenwashing", "footprint", "water use", "organic cotton", "deadstock", "repair",
            "sostenibilidad", "sostenible", "circular", "reciclado", "huella", "cadena de suministro",
            "proveedores", "trabajadores", "residuos", "segunda mano", "sostenibilita", "riciclato",
        ],
    },
    {
        "slug": "belleza",
        "label": "Belleza",
        "kw": [
            "beauty", "skincare", "skin care", "fragrance", "perfume", "perfumery", "cosmetics", "cosmetic",
            "makeup", "make-up", "lipstick", "serum", "haircare", "hair care", "scent", "nail", "spa",
            "belleza", "perfume", "cosmetica", "maquillaje", "cuidado de la piel", "fragancia",
            "bellezza", "profumo", "cosmetici",
        ],
    },
    {
        "slug": "personas",
        "label": "Movimientos",
        "kw": [
            "appointed", "appoints", "named", "names", "steps down", "step down", "resigns", "resignation",
            "hires", "hired", "departs", "departure", "leaves", "joins", "promotion", "promoted",
            "exits", "exit", "exiting", "steps aside", "vacates", "ousted",
            "chief executive", "ceo", "creative director", "creative head", "head of design", "succession",
            "obituary", "dies", "died", "passes away", "tribute",
            "nombra", "nombramiento", "dimite", "dimision", "ficha", "contrata", "deja", "se incorpora",
            "director creativo", "consejero delegado", "fallece",
            "nomina", "dimissioni", "direttore creativo",
        ],
    },
    {
        "slug": "cultura",
        "label": "Cultura",
        "kw": [
            "celebrity", "red carpet", "collaboration", "collab", "capsule", "artist", "music", "film",
            "movie", "met gala", "streetwear", "hype", "sneaker culture", "influencer", "tiktok", "viral",
            "costume", "exhibition", "museum", "art", "culture", "podcast", "documentary", "award",
            "alfombra roja", "colaboracion", "capsula", "artista", "exposicion", "museo", "premio",
            "collaborazione", "mostra", "premio",
        ],
    },
    {
        "slug": "diseno",
        "label": "Diseño",
        "kw": [
            "designer", "design", "atelier", "craftsmanship", "craft", "archive", "silhouette", "tailoring",
            "pattern", "technique", "handbag", "bag", "accessories", "jewelry", "jewellery", "watch",
            "watches", "eyewear", "denim", "knitwear", "couture technique", "review",
            "disenador", "diseno", "artesania", "archivo", "bolso", "joyas", "reloj", "gafas", "vaquero",
            "stilista", "artigianato", "borsa", "gioielli",
        ],
    },
    {
        "slug": "calzado",
        "label": "Calzado",
        "kw": [
            "footwear", "shoe", "shoes", "sneaker", "sneakers", "boot", "boots", "heel", "heels",
            "loafer", "loafers", "sandal", "sandals", "pump", "pumps", "trainers", "kicks",
            "calzado", "zapatos", "zapatillas", "botas", "tacones", "sandalias",
            "calzature", "scarpe", "sneaker",
        ],
    },
    {
        "slug": "industria",
        "label": "Industria",
        "kw": [],
    },
]

# peso editorial de cada sección al elegir la portada
CAT_BOOST = {
    "negocio": 1.2, "retail": 1.0, "sostenibilidad": 0.8, "personas": 0.6,
    "industria": 0.4, "pasarela": 0.3, "calzado": 0.2, "diseno": 0.1,
    "belleza": 0.1, "cultura": 0.0,
}

STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "at", "by", "from", "as",
    "is", "are", "was", "were", "be", "been", "its", "it", "this", "that", "new", "how", "why", "what",
    "el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "o", "que", "por", "para", "con",
    "al", "lo", "su", "sus", "se", "es", "son", "como", "mas", "pero", "il", "lo", "gli", "di", "da",
    "che", "per", "con", "una", "uno",
    "s", "will", "could", "can", "says", "said",
}

# términos que anclan una noticia al sector moda (para fuentes de retail genérico)
FASHION_RE = re.compile(
    r"(?<![a-z])(fashion|apparel|clothing|clothes|luxury|beauty|cosmetic|cosmetics|makeup|skincare"
    r"|fragrance|perfume|sneaker|sneakers|shoe|shoes|footwear|designer|couture|runway|garment|textile"
    r"|jewel|jewellery|jewelry|sportswear|athleisure|denim|jeans|moda|calzado|textil)(?![a-z])"
)

# Google News añade " - El Medio" al final del titular
PUB_SUFFIX_RE = re.compile(r"\s+[-–—]\s+[^-–—]{2,42}$")


def strip_pub_suffix(title):
    return PUB_SUFFIX_RE.sub("", title).strip() or title

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
IMG_RE = re.compile(r"""<img[^>]+?src=["']([^"']+)["']""", re.I)

# titulares que no son noticia (clasificados, listículos, how-to)
NOISE_RE = re.compile(
    r"(seeking (an? )?(intern|interns|freelance|assistant)|is (now )?hiring|now hiring"
    r"|job (opening|opportunit)|how to (wear|style|get|apply|shop)|^\d+ (best|ways)"
    r"|best (leggings|jeans|dresses|bags|shoes) (to|for)|wish list)",
    re.I,
)


# --------------------------------------------------------------------------- utilidades

def norm(s):
    """minúsculas, sin acentos, espacios simples."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    return WS_RE.sub(" ", s.lower()).strip()


def clean_text(s):
    if not s:
        return ""
    s = html.unescape(s)  # primero decodifica: algunos feeds escapan el HTML (&lt;img&gt;)
    s = TAG_RE.sub(" ", s)
    s = re.sub(r"https?://\S+", " ", s)  # fuera URLs sueltas dentro del texto
    s = html.unescape(s)
    s = s.replace("\xa0", " ")
    s = WS_RE.sub(" ", s).strip()
    return s


def _lead_rx(text):
    """Patrón que reconoce `text` al inicio de otra cadena, tolerando puntuación,
    comillas tipográficas y espacios distintos entre palabras."""
    words = re.findall(r"\w+", text or "")
    if not words:
        return None
    return re.compile(r"^\W*" + r"\W+".join(re.escape(w) for w in words) + r"(?!\w)\W*", re.I)


def strip_lead(excerpt, prefixes):
    """Quita del inicio del extracto lo que repite el medio o el titular.

    Drapers, por ejemplo, publica "Drapers <titular> <entradilla>": sin esto el
    extracto del panel y de la cápsula empieza leyendo el nombre del medio.
    """
    text = excerpt or ""
    # el más largo primero: si el titular empieza por el nombre del medio
    # ("Drapers reveals…"), quitar solo "Drapers" se comería una palabra de más
    rxs = [rx for rx in (_lead_rx(p) for p in sorted(set(prefixes), key=len, reverse=True)) if rx]
    changed = True
    while changed and text:
        changed = False
        for rx in rxs:
            m = rx.match(text)
            if m and m.end() < len(text):
                text = text[m.end():]
                changed = True
                break
    return text.strip()


def truncate(s, limit=230):
    s = clean_text(s)
    if len(s) <= limit:
        return s
    cut = s[:limit]
    if " " in cut[limit - 30:]:
        cut = cut[: cut.rfind(" ")]
    else:
        cut = cut[: limit - 1]
    return cut.rstrip(" ,;:-–—") + "…"


def local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_date(raw):
    if not raw:
        return None
    raw = raw.strip()
    # RFC 822 ("Wed, 05 Nov 2026 10:00:00 +0000")
    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(raw)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
    except Exception:
        pass
    # ISO 8601
    txt = raw.replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.fromisoformat(txt) if fmt is None else datetime.strptime(txt, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def _fetch_once(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding", "").lower() == "gzip":
            raw = gzip.decompress(raw)
        return raw


def fetch(url, retries=2):
    last = None
    for attempt in range(retries):
        try:
            return _fetch_once(url)
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last


# --------------------------------------------------------------------------- parseo de feeds

def parse_feed(raw, source):
    root = ET.fromstring(raw)
    if local(root.tag) == "feed":
        entries = [el for el in root if local(el.tag) == "entry"]
        return [atom_item(el) for el in entries]

    channel = None
    for el in root:
        if local(el.tag) == "channel":
            channel = el
            break
    container = channel if channel is not None else root
    items = [el for el in container if local(el.tag) == "item"]
    return [rss_item(el) for el in items]


def _children(el):
    out = {}
    for ch in el:
        name = local(ch.tag).lower()
        if name in out:
            continue
        out[name] = ch
    return out


def _text(el):
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def _first_img(markup):
    if not markup:
        return ""
    m = IMG_RE.search(markup)
    if not m:
        return ""
    src = html.unescape(m.group(1)).strip()
    if src.startswith("data:") or src.startswith("//"):
        return "https://" + src[2:] if src.startswith("//") else ""
    return src


def _media_image(el):
    for ch in el.iter():
        name = local(ch.tag).lower()
        if name in ("content", "thumbnail", "group"):
            for key in ("url", "href"):
                v = ch.attrib.get(key, "")
                if v and re.search(r"\.(jpe?g|png|webp|avif)(\?|$)", v, re.I):
                    return html.unescape(v)
    return ""


def _link_from(el):
    for ch in el:
        if local(ch.tag).lower() == "link":
            href = ch.attrib.get("href")
            if href:
                rel = ch.attrib.get("rel", "alternate")
                if rel == "alternate":
                    return href.strip()
            txt = (ch.text or "").strip()
            if txt.startswith("http"):
                return txt
    return ""


def rss_item(el):
    kids = _children(el)
    title = clean_text(_text(kids.get("title")))
    link = _link_from(el) or _text(kids.get("guid"))
    raw_body = _text(kids.get("encoded")) or _text(kids.get("description")) or _text(kids.get("summary"))
    image = (
        _media_image(el)
        or _first_img(_text(kids.get("encoded")))
        or _first_img(_text(kids.get("description")))
    )
    date = (
        parse_date(_text(kids.get("pubdate")))
        or parse_date(_text(kids.get("date")))
        or parse_date(_text(kids.get("published")))
        or parse_date(_text(kids.get("updated")))
    )
    return {
        "title": title,
        "link": (link or "").strip(),
        "body": raw_body,
        "image": image,
        "published": date,
    }


def atom_item(el):
    kids = {}
    for ch in el:
        name = local(ch.tag).lower()
        kids.setdefault(name, ch)
    title = clean_text(_text(kids.get("title")))
    link = _link_from(el)
    body = _text(kids.get("content")) or _text(kids.get("summary"))
    image = _media_image(el) or _first_img(body)
    date = parse_date(_text(kids.get("published"))) or parse_date(_text(kids.get("updated")))
    return {
        "title": title,
        "link": (link or "").strip(),
        "body": body,
        "image": image,
        "published": date,
    }


# --------------------------------------------------------------------------- clasificación

def _prep_kw():
    for c in CATS:
        if not c["kw"]:
            c["re"] = None
            continue
        alts = []
        for k in sorted(c["kw"], key=len, reverse=True):
            k = norm(k)
            if not k:
                continue
            alts.append(re.escape(k).replace(r"\ ", r"\s+"))
        c["re"] = re.compile(r"(?<![a-z0-9])(?:" + "|".join(alts) + r")(?![a-z0-9])", re.I)


_prep_kw()


def classify(title, body, strict=False):
    """Devuelve la sección principal, ordenada por puntuación.

    strict=True (revistas de consumo): solo el titular decide, porque el cuerpo
    de un artículo de lifestyle menciona 'store', 'collection' o 'beauty' y
    ensucia la clasificación.
    """
    nt = " " + norm(title) + " "
    nb = " " + norm(truncate(body, 450)) + " "
    scored = []
    for idx, c in enumerate(CATS):
        if not c["re"]:
            continue
        hits_t = len(c["re"].findall(nt))
        hits_b = 0 if strict else len(c["re"].findall(nb))
        if not hits_t and not hits_b:
            continue
        score = min(hits_t * 3.0, 6.0) + min(hits_b * 0.4, 1.8) - idx * 0.01
        scored.append((score, c["slug"]))
    scored.sort(reverse=True)
    if not scored:
        return ["industria"]
    # revistas de consumo: solo si el titular apunta a un tema de industria
    if strict and scored[0][1] not in ("negocio", "retail", "sostenibilidad", "personas"):
        return ["industria"]
    return [slug for _, slug in scored[:3]]


def tokens(title):
    return {w for w in norm(title).split() if len(w) > 2 and w not in STOP and not w.isdigit()}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / len(a | b)


def is_dup(a, b):
    t1, t2 = a["_tok"], b["_tok"]
    if not t1 or not t2:
        return False
    short, long_ = (t1, t2) if len(t1) <= len(t2) else (t2, t1)
    # un titular contenido en otro con 3+ palabras significativas = misma noticia
    if len(short) >= 3 and short.issubset(long_):
        return True
    return jaccard(t1, t2) >= 0.5


def canonical(link):
    link = (link or "").strip().lower()
    link = re.sub(r"^https?://", "", link)
    link = re.sub(r"^www\.", "", link)
    link = link.split("#")[0]
    link = re.sub(r"\?.*$", "", link)
    return link.rstrip("/")


TRACKING = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source", "smid", "partner", "cmpid"}


def clean_link(link):
    """Quita parámetros de seguimiento (utm_*, fbclid...) para que el enlace quede limpio."""
    try:
        parts = urllib.parse.urlsplit(link)
        if not parts.query:
            return link
        keep = [
            (k, v)
            for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
            if not k.lower().startswith("utm_") and k.lower() not in TRACKING
        ]
        return urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(keep), "")
        )
    except Exception:
        return link


# tipo de acontecimiento: sirve para reconocer la misma noticia contada por varios medios
EVENTS = [
    ("resultados", re.compile(
        r"(?<![a-z])(sales|revenue|revenues|earnings|profit|quarter|quarterly|q[1-4]|outlook|forecast"
        r"|results|guidance|margin|turnover|ingresos|ventas|resultados|fatturato|utile|bilancio)(?![a-z])")),
    ("fichajes", re.compile(
        r"(?<![a-z])(names|named|appoints|appointed|exits|departs|steps down|resigns|hires|joins"
        r"|director creativo|nombra|nombramiento|dimite|nomina|dimissioni|direttore creativo)(?![a-z])")),
    ("operacion", re.compile(
        r"(?<![a-z])(acquires|acquisition|merger|stake|takeover|investment|funding|ipo|buyout"
        r"|adquiere|compra|fusion|inversion)(?![a-z])")),
]


def event_class(title):
    nt = norm(title)
    for name, rx in EVENTS:
        if rx.search(nt):
            return name
    return None


def lead_entity(title):
    for w in norm(title).split():
        if len(w) > 2 and w not in STOP and not w.isdigit():
            return w
    return None


# --------------------------------------------------------------------------- pipeline

def build(sources, days):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    results, failures = [], []

    def work(src):
        errors = []
        urls = [src["url"]] + ([src["fallback"]] if src.get("fallback") else [])
        for idx, url in enumerate(urls):
            try:
                parsed = parse_feed(fetch(url), src)
                if parsed:
                    return src, parsed, None, idx > 0
                errors.append("feed vacio")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{type(exc).__name__}: {exc}")
        return src, [], " | ".join(errors), False

    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for src, parsed, err, mirrored in ex.map(work, sources):
            if err and not parsed:
                failures.append((src["name"], err))
                continue
            results.append((src, parsed, mirrored))

    items, seen_links = [], set()
    for src, parsed, mirrored in results:
        kind = src.get("kind", "trade")
        kept = 0
        for it in parsed:
            title = strip_pub_suffix(it["title"]) if mirrored else it["title"]
            link = it["link"]
            if not title or not link.startswith("http"):
                continue
            if NOISE_RE.search(title):
                continue
            if src.get("generic") and not FASHION_RE.search(norm(title)):
                continue
            pub = it["published"] or now
            if pub < cutoff or pub > now + timedelta(days=1):
                continue
            can = canonical(link)
            if not can or can in seen_links:
                continue
            # una noticia = una sección (la de mayor puntuación)
            tags = classify(title, it["body"], strict=(kind == "consumer"))[:1]
            # las revistas de consumo solo entran si la noticia es de industria
            if tags[0] == "industria" and kind == "consumer":
                continue
            seen_links.add(can)
            body = strip_lead(clean_text(it["body"]), [src["name"], src["short"], title])
            excerpt = truncate(body)
            if mirrored and norm(excerpt).startswith(norm(title)[:40]):
                excerpt = ""  # el espejo solo devuelve "Titular - Medio"
            if len(excerpt) < 40:
                excerpt = ""
            image = it["image"] or ""
            if image and not image.startswith("http"):
                image = urllib.parse.urljoin(link, image)  # rutas relativas de algunos feeds
            items.append(
                {
                    "title": title,
                    "link": clean_link(link),
                    "excerpt": excerpt,
                    "image": image,
                    "published": pub,
                    "source": src["short"],
                    "source_name": src["name"],
                    "kind": kind,
                    "mirror": mirrored,
                    "weight": float(src["weight"]),
                    "lang": src["lang"],
                    "region": src["region"],
                    "tags": tags,
                    "_tok": tokens(title),
                    "_ev": (lead_entity(title), event_class(title)),
                }
            )
            kept += 1
            if kept >= MAX_PER_FEED:
                break

    merged = merge_items(items)

    for it in merged:
        it.pop("_tok", None)
        it.pop("_ev", None)
        it["also"] = it.get("also", [])
        it["published"] = it["published"].isoformat().replace("+00:00", "Z")
        # id estable: hash del enlace (hash() de Python cambia en cada proceso y
        # rompería la deduplicación del archivo histórico)
        it["id"] = hashlib.sha1(it["link"].encode("utf-8")).hexdigest()[:12]
        it["score"] = round(
            it["weight"] * 1.2
            + _recency_bonus(it["published"])
            + CAT_BOOST.get(it["tags"][0], 0.0)
            + 0.75 * len(it["also"])  # cuantos más medios lo cubren, más importante es
            + (0.35 if it["image"] else 0)
            + (0.15 if 30 <= len(it["title"]) <= 115 else 0)
            + (0.2 if it["excerpt"] else 0),
            3,
        )

    merged.sort(key=lambda x: (x["published"], x["score"]), reverse=True)
    return merged, failures


# campos que definen "de qué medio es" una noticia; se intercambian en bloque
OWN_FIELDS = (
    "title", "link", "excerpt", "image", "published", "source", "source_name",
    "kind", "mirror", "weight", "lang", "region", "tags",
)


def _promote(twin, it):
    """`it` trae enlace directo y `twin` (la principal) vino por el espejo de Google.

    La versión directa pasa a ser la principal: su enlace es el real y estable
    (los de news.google.com son redirecciones opacas que pueden caducar) y trae
    entradilla e imagen propias. El medio del espejo queda en "también en".
    """
    old = {k: twin[k] for k in OWN_FIELDS}
    for k in OWN_FIELDS:
        twin[k] = it[k]
    return old


def merge_items(items):
    """Fusiona la misma noticia publicada por varios medios. Devuelve la lista sin duplicados."""
    # orden editorial: primero lo de más peso y más reciente -> sobrevive el mejor
    items.sort(key=lambda x: (-x["weight"], -x["published"].timestamp()))

    merged, by_event = [], {}
    for it in items:
        twin = None
        ent, ev = it["_ev"]
        # misma entidad + mismo tipo de acontecimiento + misma franja horaria = misma noticia
        if ent and ev:
            for cand in by_event.get((ent, ev), []):
                if cand["source_name"] == it["source_name"]:
                    continue
                gap = abs((cand["published"] - it["published"]).total_seconds())
                if gap <= 48 * 3600:
                    twin = cand
                    break
        if twin is None:
            for kept in merged:
                # dos titulares parecidos del mismo medio son una serie, no un duplicado
                if kept["source_name"] == it["source_name"]:
                    continue
                if is_dup(it, kept):
                    twin = kept
                    break
        if twin is None:
            merged.append(it)
            if ent and ev:
                by_event.setdefault((ent, ev), []).append(it)
            continue
        other = it
        if twin["mirror"] and not it["mirror"]:
            # la principal solo tenía el enlace de Google: gana la versión directa
            other = _promote(twin, it)
        # se conserva el extracto del medio principal (y en su idioma)
        if not twin["excerpt"] and other["excerpt"] and other["lang"] == twin["lang"]:
            twin["excerpt"] = other["excerpt"]
        if not twin["image"] and other["image"]:
            twin["image"] = other["image"]
        also = twin.setdefault("also", [])
        if twin["source_name"] in also:
            also.remove(twin["source_name"])
        if other["source_name"] not in also and other["source_name"] != twin["source_name"]:
            also.append(other["source_name"])
    return merged


def _recency_bonus(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return 0.0
    hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    if hours <= 6:
        return 2.0
    if hours <= 18:
        return 1.4
    if hours <= 36:
        return 0.9
    if hours <= 72:
        return 0.4
    return 0.0


def video_for(out_dir, date_str):
    """Enlace relativo a la cápsula del día, si ya se generó."""
    p = out_dir / "videos" / f"{date_str}.mp4"
    if p.exists():
        return f"videos/{date_str}.mp4"
    return None


def pick_hero(items):
    ranked = sorted(items, key=lambda x: x["score"], reverse=True)
    if not ranked:
        return []
    # la noticia principal debe tener imagen: la tarjeta grande se apoya en ella
    lead = next((it for it in ranked if it["image"]), ranked[0])
    hero, used = [lead], {lead["tags"][0]}
    for it in ranked:
        if len(hero) == 3:
            break
        if it in hero or it["tags"][0] in used:
            continue
        hero.append(it)
        used.add(it["tags"][0])
    for it in ranked:
        if len(hero) == 3:
            break
        if it not in hero:
            hero.append(it)
    return hero[:3]


# --------------------------------------------------------------------------- salidas

ARCHIVE_COLS = [
    "id", "published", "title", "source", "section", "lang",
    "link", "excerpt", "image", "also", "mirror", "weight",
]


def update_archive(items, root):
    """Acumula el corpus histórico: un JSON por línea y un CSV para Excel/pandas."""
    d = root / "datos"
    d.mkdir(exist_ok=True)
    jl = d / "noticias.jsonl"

    seen = set()
    seen_same = set()  # mismo medio + mismo titular + mismo día (directo vs espejo)

    def clave(r):
        return "|".join([
            r.get("source", ""),
            norm(r.get("title", ""))[:70],
            str(r.get("published", ""))[:10],
        ])

    if jl.exists():
        for line in jl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            seen.add(row["id"])
            seen_same.add(clave(row))

    nuevos = 0
    with jl.open("a", encoding="utf-8") as f:
        for it in sorted(items, key=lambda x: x["published"]):
            row = {
                "id": it["id"],
                "published": it["published"],
                "title": it["title"],
                "source": it["source"],
                "section": it["tags"][0],
                "lang": it["lang"],
                "link": it["link"],
                "excerpt": it["excerpt"],
                "image": it["image"],
                "also": "; ".join(it["also"]),
                "mirror": it["mirror"],
                "weight": it["weight"],
            }
            if row["id"] in seen or clave(row) in seen_same:
                continue
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            seen.add(row["id"])
            seen_same.add(clave(row))
            nuevos += 1

    rows = [json.loads(l) for l in jl.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows.sort(key=lambda r: r.get("published", ""), reverse=True)
    with (d / "noticias.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ARCHIVE_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return nuevos, len(rows)


def write_digest(items, meta, path):
    lines = []
    d = datetime.fromisoformat(meta["generated"].replace("Z", "+00:00"))
    fecha = d.strftime("%d/%m/%Y")
    lines.append(f"# Moda Radar · {fecha}")
    lines.append("")
    lines.append(
        f"**{len(items)} noticias · {meta['sources_ok']} fuentes · ventana de {meta['days']} días**"
    )
    if meta["sources_failed"]:
        lines.append("")
        lines.append(f"_Fuentes que fallaron esta edición: {', '.join(meta['sources_failed'])}_")
    lines.append("")

    if meta["hero"]:
        lines.append("## Lo esencial")
        lines.append("")
        for it in meta["hero"]:
            lines.append(f"### [{it['title']}]({it['link']})")
            lines.append(f"_{it['source']}{' · también en ' + ', '.join(it['also']) if it['also'] else ''}_")
            if it["excerpt"]:
                lines.append("")
                lines.append(it["excerpt"])
            lines.append("")

    for cat in CATS:
        group = [it for it in items if cat["slug"] in it["tags"]]
        if not group:
            continue
        lines.append(f"## {cat['label']} ({len(group)})")
        lines.append("")
        for it in group[:20]:
            hora = datetime.fromisoformat(it["published"].replace("Z", "+00:00")).strftime("%H:%M")
            extra = f" · también en {', '.join(it['also'])}" if it["also"] else ""
            lines.append(f"- **[{it['title']}]({it['link']})** — {it['source']}{extra} · {hora} UTC")
        if len(group) > 20:
            lines.append(f"- _…y {len(group) - 20} más en el panel_")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Fuentes")
    lines.append("")
    per = {}
    for it in items:
        per[it["source"]] = per.get(it["source"], 0) + 1
    for name, n in sorted(per.items(), key=lambda kv: -kv[1]):
        lines.append(f"- {name}: {n}")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Radar diario de noticias de moda.")
    ap.add_argument("--days", type=int, default=4, help="ventana de días (defecto 4)")
    ap.add_argument("--out", default="docs", help="carpeta de salida del panel (defecto docs)")
    ap.add_argument("--digests", default="digests", help="carpeta de digests Markdown")
    ap.add_argument("--sources", default="sources.json", help="catálogo de fuentes")
    ap.add_argument("--check", action="store_true", help="solo validar las fuentes y salir")
    ap.add_argument("--render-only", action="store_true", help="regenerar el panel desde latest.json")
    ap.add_argument("--limit", type=int, default=0, help="limitar nº de fuentes (pruebas)")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    from pathlib import Path

    root = Path(__file__).resolve().parent
    cfg = json.loads((root / args.sources).read_text(encoding="utf-8"))
    sources = cfg["sources"]
    if args.limit:
        sources = sources[: args.limit]

    if args.check:
        ok = bad = 0
        for src in sources:
            try:
                parsed = parse_feed(fetch(src["url"]), src)
                n = len(parsed)
                dates = [p["published"] for p in parsed if p["published"]]
                newest = max(dates).strftime("%Y-%m-%d %H:%M") if dates else "sin fecha"
                print(f"  OK  {n:>3} items  {src['name']:<26} {newest}")
                ok += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  ERR              {src['name']:<26} {type(exc).__name__}: {exc}")
                bad += 1
        print(f"\n{ok} fuentes OK · {bad} con error")
        return 0 if ok else 1

    if args.render_only:
        payload = json.loads((root / args.out / "data" / "latest.json").read_text(encoding="utf-8"))
        items = payload["items"]
        gen = payload.get("generated", "")
        meta = {
            "generated": gen,
            "generated_date": gen[:10],
            "generated_human": datetime.fromisoformat(gen.replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M UTC"),
            "days": payload.get("days", args.days),
            "sources_ok": payload.get("sources_ok", 0),
            "sources_failed": payload.get("sources_failed", []),
            "hero": pick_hero(items),
            "category_order": CATS,
            "video": video_for(root / args.out, gen[:10]),
        }
        (root / args.out / "index.html").write_text(ui.render(items, meta), encoding="utf-8")
        print(f"panel regenerado ({'con' if meta['video'] else 'sin'} capsula)")
        return 0

    print(f"moda-radar · {len(sources)} fuentes · ventana {args.days} días")
    items, failures = build(sources, args.days)
    for name, err in failures:
        print(f"  ! {name}: {err}")

    now = datetime.now(timezone.utc)
    out = root / args.out
    hero = pick_hero(items)
    meta = {
        "generated": now.isoformat().replace("+00:00", "Z"),
        "generated_date": now.strftime("%Y-%m-%d"),
        "generated_human": now.strftime("%d/%m/%Y %H:%M UTC"),
        "days": args.days,
        "sources_ok": len(sources) - len(failures),
        "sources_failed": [n for n, _ in failures],
        "hero": hero,
        "category_order": CATS,
        "video": video_for(out, now.strftime("%Y-%m-%d")),
    }

    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(ui.render(items, meta), encoding="utf-8")

    payload = {
        "generated": meta["generated"],
        "days": args.days,
        "count": len(items),
        "sources_ok": meta["sources_ok"],
        "sources_failed": meta["sources_failed"],
        "items": items,
    }
    blob = json.dumps(payload, ensure_ascii=False, indent=1)
    (out / "data" / "latest.json").write_text(blob, encoding="utf-8")
    (out / "data" / f"news-{now.strftime('%Y-%m-%d')}.json").write_text(blob, encoding="utf-8")

    write_digest(items, meta, root / args.digests / f"{now.strftime('%Y-%m-%d')}.md")

    nuevos, acumuladas = update_archive(items, root)

    print(f"\n{len(items)} noticias · {meta['sources_ok']}/{len(sources)} fuentes · {len(failures)} errores")
    print(f"panel   -> {out / 'index.html'}")
    print(f"digest  -> {root / args.digests / (now.strftime('%Y-%m-%d') + '.md')}")
    print(f"archivo -> {root / 'datos' / 'noticias.jsonl'} (+{nuevos} nuevas, {acumuladas} en total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
