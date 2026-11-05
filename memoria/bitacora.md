# Bitácora

## 2026-11-05 · construcción inicial

**Qué se hizo**
- Se probaron 46 URLs de RSS candidatas; solo 25 respondían y 7 más se recuperaron con
  variantes (`/feed/rss`, `/rss/all.xml`, etc.). Total: 32 fuentes vivas.
- Descartadas por no tener RSS abierto: Vogue Business, The Cut, Modaes, FashionNetwork,
  Just Style, Sourcing Journal, Jing Daily, W Magazine, Glamour, Nylon, Paper, SSENSE.
- Pipeline en Python sin dependencias: descarga en paralelo con reintentos, limpieza de
  HTML, ventana de días, deduplicación, clasificación por palabras clave y render estático.

**Decisiones**
- Una noticia = una sección. Antes un ítem fusionado acumulaba etiquetas y salía repetido
  en varias secciones.
- No se fusionan dos titulares parecidos del mismo medio: son series (Power 100, etc.),
  no duplicados.
- Deduplicación en dos capas: similitud de titular (Jaccard ≥ 0.5 o continencia con 3+
  palabras) y entidad + tipo de acontecimiento (resultados / fichajes / operaciones) en
  una franja de 48 h. La segunda capa es la que une la misma noticia entre medios e
  incluso entre idiomas (caso Piccioli: WWD + BoF + Pambianco + Elle).
- Revistas de consumo (Vogue, Bazaar, GQ, Elle...) solo entran si el titular apunta a
  negocio, retail, sostenibilidad o fichajes. Sin este filtro se colaban listículos de
  compras y pasarelas de famosas.
- Fuentes de retail genérico (CNBC, Retail Dive, Retail Gazette) exigen una palabra
  ancla de moda en el titular; si no, entraba una noticia sobre Expedia.
- Umbrales: `MAX_PER_FEED = 15`, ventana de 4 días, Jaccard 0.5, continencia 3 tokens.

**Fallos corregidos**
- `Accept-Encoding: gzip` provocaba un bucle de redirección en Textile World.
- Los extractos arrastraban URLs de imagen cuando el feed escapaba el HTML: ahora se
  desescapa antes de quitar etiquetas.
- Las URLs llevaban `utm_*`: se limpian antes de guardar.
- El extracto fusionado podía venir en otro idioma que el titular: se conserva el del
  medio principal.

**Pendiente**
- Publicar en GitHub y verificar la primera ejecución del cron.
- Revisar si Hypebeast sigue bloqueando desde los runners de GitHub.
- Valorar un histórico navegable (hoy solo se guardan los JSON por día y los digests).

## 2026-11-05 · puesta en producción

- Repo público `mexicanfasionstreet-cyber/moda-radar`. Pages sirve desde `/docs`; Actions
  con permiso de escritura. URL: https://mexicanfasionstreet-cyber.github.io/moda-radar/
- Primera ejecución en la nube: 124 noticias, 29/32 fuentes. Fallos: BoF 403, Hypebeast
  405, Textile World 301. Los tres funcionan desde casa: el bloqueo es por IP de
  datacenter (WAF), no por cabeceras. No se arregla cambiando el user-agent.
- Solución: campo `fallback` en `sources.json`. BoF → Google News RSS (`site:`), Textile
  World → Bing News RSS. Si la fuente primaria falla se usa el espejo y el ítem se marca
  `mirror: true`.
- Hypebeast se queda sin espejo a propósito: su feed de Google News arrastra gaming, cine
  y deporte (Apple, Lakers, GTA VI) y metía ruido en Negocio.
- Los espejos no traen imagen ni extracto real: Google devuelve "Titular - Medio", así que
  se recorta el sufijo y se descarta el extracto cuando repite el titular.
- Nuevo disparador `push` limitado a `aggregate.py`, `ui.py`, `sources.json` y el propio
  workflow: un cambio de código relanza la edición sin pulsar nada (y el commit del bot no
  lo dispara, porque no toca esas rutas).
- Corregido: las imágenes con ruta relativa (`../storage/...` en Textile Today) se
  resuelven contra la URL del artículo; las tarjetas sin resumen ya no dejan un hueco.
- Estado: 137 noticias, 31 fuentes (solo falta Hypebeast).

## 2026-11-05 · capa de datos (el corpus)

Objetivo del usuario: no el panel ni el bot, sino **acumular información** para construir
encima. El panel es solo la vista.

- Nuevo `datos/noticias.jsonl`: append-only, una noticia por línea, nunca se reescribe.
  `datos/noticias.csv` se regenera entero desde el `.jsonl` (con BOM para Excel).
  `docs/data/news-*.json` sigue guardando la edición completa del día.
- **Bug corregido antes del primer dato**: el `id` era `hash(link)`, y el hash de Python
  por defecto cambia en cada proceso. Los ids no habrían sido estables entre ejecuciones
  y el corpus habría duplicado noticias. Ahora es `sha1(link)[:12]`.
- Doble deduplicación del corpus: por `id` y por (medio + titular + día). La segunda es
  necesaria porque BoF entra unos días por el espejo (enlace de Google) y otros directo:
  el mismo artículo tiene dos enlaces distintos.
- El workflow hace `git add docs digests datos`.
- `datos/README.md` documenta los 12 campos y trae ejemplos en pandas / Excel / PowerShell.
- Crecimiento previsto: ~90 KB/día, ~30 MB/año. Suficiente; si molesta, se rota por año.

## 2026-11-05 · cápsula en vídeo

Objetivo: minicápsulas diarias con imágenes + voz en off, sin cámara ni editor.
Decisiones: vertical 1080x1920, ~45 s, en GitHub Actions, guion con IA, voz
`es-MX-DaliaNeural` al +8%.

- `capsule.py` hace todo: selección → guion → TTS → composición → montaje con ffmpeg.
- Selección **por imagen primero**: BoF puntúa altísimo pero su CDN a veces no responde;
  si no hay foto usable, el ítem baja al final.
- El texto de pantalla se compone con Pillow en un PNG transparente y se superpone fijo,
  mientras la foto hace un paneo lento. Así el titular no se mueve ni se deforma.
- **Bug que costó tres renders**: faltaba `from PIL import ... ImageOps`, y el `except`
  silencioso del bloque de apertura convertía el error en "sin imagen". Todas las
  diapositivas salían con degradado. Regla nueva: los `except` de imagen registran el
  motivo antes de caer al degradado.
- **Bug de bandas en el degradado**: `ImageDraw` *reemplaza* el alfa, no lo mezcla. Pintar
  velo + sombra + degradado en tres pasadas dejaba escalones visibles. Ahora se calcula
  una única rampa por fila.
- Sin clave de IA el guion sale de plantilla y los titulares van en inglés (la voz es
  española). Es un modo de emergencia, no el modo normal.
- El vídeo vive en `docs/videos/`, se sirve por Pages y el panel enlaza el del día con
  `aggregate.py --render-only` (se rehace el HTML al terminar el vídeo).
- Rotación: se conservan los 10 últimos mp4. Peso ~2 MB/día; el historial de Git crece.
  Si algún día molesta, la salida limpia es subirlos como *release assets* o artefactos.
