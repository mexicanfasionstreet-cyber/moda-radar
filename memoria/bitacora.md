# Bitácora

## 2026-11-07 · la rotación del Release no borraba nada

- El paso que elimina las cápsulas viejas filtraba con `^AAAA-MM-DD${sufijo}\.mp4$`, un
  patrón que solo casaba con los nombres anteriores a las franjas. Desde que los archivos
  se llaman `AAAA-MM-DD-noche.mp4`, **no coincidía con ninguno** y el Release crecía
  ~23 MB al día (unos 8 GB al año).
- Ahora es `^AAAA-MM-DD(-(manana|mediodia|noche))?${sufijo}\.mp4$`: se siguen borrando los
  más antiguos y se conservan 60 por edición (~20 días).
- Comprobado con nombres reales: con sufijo vacío casa las generales y **no** las `-latam`;
  con `-latam` solo casa las de LatAm.
- No hizo falta limpiar nada a mano: había 16 archivos, por debajo de los 60.

## 2026-11-06 · publicar solo en YouTube e Instagram

- `publicar.py` sube cada cápsula: YouTube por `videos.insert` resumable y Stories de
  Instagram con contenedor `media_type=STORIES`, sondeo de estado y `media_publish`.
- **Límite verificado en la doc de Meta**: las Stories son de 3 a 60 s, así que una
  cápsula de 65-70 s se parte en dos tarjetas con ffmpeg (re-codificando para que el corte
  sea exacto).
- **Una Story no admite pie de foto ni enlace**: los textos del kit solo sirven para
  YouTube. En Instagram todo tiene que estar dentro del vídeo, que es lo que ya se hace.
- **Meta no acepta subida directa**: descarga el vídeo de una URL pública. Por eso el
  script sube cada trozo al Release `capsulas` como asset, publica y lo borra enseguida.
- YouTube: un Short es cualquier vertical de hasta 3 min; no hay endpoint aparte. Cuota
  1.600 unidades por subida → las 6 diarias son 9.600 de 10.000, sin margen.
- Antiduplicados: `docs/videos/publicadas.json` con ventana de 20 h.
- Solo publica en ejecuciones **programadas**; en manual hay que marcar la casilla, para
  que una prueba de código no acabe en las redes.
- `herramientas/token-youtube.py` resuelve el refresh token con el flujo de dispositivo
  (sin servidor local: un código que se escribe en google.com/device desde el móvil).

## 2026-11-08 · más búsquedas por tema (escena mexicana)

Pedido: diseñadores mexicanos, moda Tijuana, segunda mano, bazares, takeovers, fashion
shows. Probadas con *Probar fuentes* (titulares de muestra) y afinadas:
- Tijuana: "desfile" traía los desfiles cívicos (Día de Muertos, 16 de septiembre) y "moda"
  o "modelo" sueltos traían "café de moda" o el "modelo de gobierno" del alcalde. Se queda
  la búsqueda vieja y se suma *Diseño y pasarela en Tijuana* (pasarela, desfile de moda,
  diseñador/a tijuanense...), con `short` "Tijuana" para la prioridad de la cápsula.
- Fashion shows: sin Victoria's Secret ni "dónde ver" ni catrinas. NOISE_RE: "a qué hora",
  "dónde ver".
- Bazares y Takeovers/pop-ups con `generic: true` (el titular debe hablar de moda): fuera
  los pop-ups de BTS o Harry Styles.
- Probadas y pendientes de que el usuario elija (en `herramientas/fuentes-temas.json`):
  streetwear, textil artesanal, Intermoda y ferias, Baja California, San Diego, industria
  textil, modelos mexicanas.

## 2026-11-08 · las cápsulas repetían noticias

Queja del usuario: "está repitiendo notas". Medido en las 12 cápsulas del 6 al 8: 24 de 60
noticias ya habían salido antes (The IQ Collection en 6 cápsulas LatAm, El Trompo en 5).

Causas:
- Ventana de 10 h: noche (19:00) → mañana (07:00) son 12 h, y mañana → noche también;
  solo protegía franjas seguidas.
- Si quedaban menos de 3 nuevas, se "permitía repetir para no dejar la cápsula vacía":
  la LatAm (≈14 candidatas para 3 franjas) caía ahí casi siempre.
- Solo comparaba el enlace exacto: la misma historia en otro medio, en otro idioma o con
  el enlace de Google ya resuelto pasaba como nueva (horóscopo de Vogue UK y Vogue US).
- Cada edición llevaba su registro: lo de la general podía salir en la LatAm y van al
  mismo canal y a la misma cuenta.
- Las corridas que no publican (push de código) también apuntaban sus noticias.

Arreglo (`capsule.py`):
- Ventana de **72 h** (`--ventana-repe`), registro guardado 7 días.
- **Un solo registro** `docs/videos/usadas.json` para las dos ediciones, con enlace
  canónico y titular. Lee el formato viejo y migra `usadas-latam.json`; para entradas
  viejas sin titular lo busca en el corpus.
- **Misma historia** (`misma_historia`): ≥3 palabras significativas en común y ≥50 % del
  titular más corto. Probado con 172 titulares reales: junta las 8 versiones de Martine
  Rose/Balenciaga (en inglés, español e italiano) sin confundir noticias distintas.
  También dentro de una cápsula: una sola versión por historia.
- **Sin relleno**: con menos de 3 noticias nuevas la franja no lleva cápsula (y
  `publicar.py` ya se salta lo que no tiene vídeo).
- Solo se apuntan como emitidas las cápsulas que se publican (`--registrar`, que el
  workflow activa en las programadas y en las manuales con "publicar").
- Simulación de 4 franjas seguidas con los datos reales: 0 repetidas. Pero la LatAm se
  queda sin cápsula: sus 14 candidatas ya salieron en los últimos 3 días. La región da
  noticias para ~1 cápsula al día, no para 3.

## 2026-11-06 · marca TBA y fechas locales

- El logo sustituye a "MODA/RADAR" en pantalla. Se usan **dos versiones**: `logo-tba.png`
  (completo, con la línea *THE BORDER ARCHIVE*, para la tarjeta de cierre) y
  `logo-tba-solo.png` (solo las letras, para la esquina). A 72 px de alto la línea fina
  del logo era ilegible, así que en la esquina va recortada a 86 px.
- El PNG transparente se generó desde el original blanco sobre negro usando la
  luminancia como canal alfa: así no queda el cuadrado negro sobre las fotos.
- El archivo de textos firma con `MARCA["nombre"] · MARCA["handle"]`
  (The Border Archive · @theborderarchive). Se cambia en el bloque `MARCA` de `capsule.py`.
- **Fechas locales**: la franja de noche es a las 19:00 CDMX = 01:00 UTC del día
  siguiente, así que los archivos se llamaban con la fecha del día siguiente. Ahora
  `fecha_local()` (capsule) y `fecha_mx()` (aggregate) convierten a America/Mexico_City,
  que es la misma regla que usa el panel para encontrar el vídeo.

## 2026-11-06 · tres franjas al día y textos para publicar

- El cron pasa de una a tres ejecuciones (13:00, 19:00 y 01:00 UTC = 07:00, 13:00 y
  19:00 en Ciudad de México). Con dos ediciones son **seis cápsulas al día**.
- `--franja` (dia | manana | mediodia | noche) añade sufijo al nombre
  (`2026-11-06-manana.mp4`, `-latam`), a la portada, al `index-*.json` y al `.txt`.
- **No repetir**: `docs/videos/usadas{,-latam}.json` guarda enlace → fecha de emisión y
  `quitar_repetidas()` descarta lo visto en las últimas `--ventana-repe` horas (10 por
  defecto). Si quedan menos de 3 noticias frescas se permite repetir, para no emitir una
  cápsula vacía. La lista se poda a 3 días.
- **Kit de publicación**: `escribir_kit()` deja un `.txt` con título, descripción con los
  cinco enlaces, hashtags y duración. Usa el titular **original** (`headline`), no el
  recortado de pantalla. El panel lo enlaza con el botón "Textos para publicar".
- `aggregate.video_for()` ahora busca la cápsula más reciente del día en orden
  noche → mediodía → mañana → día.
- La franja se calcula en el workflow con la hora UTC (`<6` noche, `<16` mañana, resto
  mediodía), así que `workflow_dispatch` también acierta sin parámetros.
- **Filtro**: se colaba "Editor's Comment"/"Comentario del editor" como noticia; añadido
  al patrón de relleno.

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

## 2026-11-05 · segunda vuelta de la cápsula (queja del usuario)

Síntomas: "no habla bien, no está en español, una nota sin imagen, solo lee encabezados".

Diagnóstico: sin clave de IA, la plantilla leía **titulares en inglés con voz española**
(exactamente eso es "no se entiende"). Y solo leía el titular porque no había resumen.

Cambios:
- **Traducción sin clave**: `translate_es()` usa el endpoint público de Google
  (`translate_a/single`, cliente gtx). Con 3 reintentos porque corta si se piden muchas
  seguidas. Así el modo sin IA también sale en español.
- **Resumen, no titular**: la plantilla usa titular traducido + primera frase de la
  entradilla, recortada a 18 palabras (`clip_words`). Con IA el prompt pide 22-32
  palabras explicando qué pasó y por qué importa.
- **Cortador de frases propio**: `re.split` cortaba en "Dr. Martens" y dejaba la noticia
  sin resumen. Ahora `first_sentence()` busca el punto después del carácter 40.
- **Imagen que faltaba**: `resolve_images()` busca `og:image` en la página de las
  noticias sin foto en el RSS. Pasó de 78 a 92 noticias con imagen de 134 (WWD es el
  caso típico: nunca publica la foto en el feed).
- **Ritmo**: velocidad de +8% a +5% y 0,5 s de aire entre planos.
- **Duración**: la primera versión con resúmenes se iba a 79 s; recortando a 18 palabras
  queda en 62 s.
- `--no-llm` ahora fuerza la plantilla (antes se llamaba igual pero no hacía nada).

## 2026-11-05 · imagen que falta y música

- **Nota sin imagen**: The Industry publica en el RSS miniaturas `-150x150.jpg`. El filtro
  de "mínimo 420 px" las descartaba y la diapositiva caía al degradado. Ahora hay cadena
  de respaldo: URL del RSS → misma URL sin el sufijo de miniatura (`-150x150` fuera, que
  en WordPress apunta al original) → `og:image` de la página → y solo si todo falla, la
  miniatura ampliada y desenfocada como fondo, que se ve intencionado.
- **Música**: `musica/fondo.mp3` en bucle, con entrada de 2 s y salida de 3 s, mezclada a
  −30 dB (unos 14 dB por debajo de la voz). La ganancia se calcula midiendo la pista, así
  que vale cualquier mp3 que se deje en la carpeta. Banderas: `--sin-musica` y `--music`.
- **Bug**: el clamp de ganancia era `max(-6, …)`, así que nunca atenuaba más de 6 dB y la
  música quedaba a −26 dB (demasiado presente). Corregido a −30.
- Pistas CC0 de Freesound vía Openverse. Se pueden sustituir sin tocar código.

## 2026-11-05 · revisión: vídeos fuera de Git, enlaces y extractos

- **Vídeos fuera del historial**: cada mp4 (~3,8 MB) se commiteaba. Aunque se rotaran,
  los borrados se quedan en Git: ~1,4 GB al año. Ahora `docs/videos/*.mp4` y las portadas
  están en `.gitignore`; el workflow sube la cápsula al Release `capsulas` (conserva 60) y
  publica `docs/` en Pages con `actions/deploy-pages`, vídeo del día incluido.
  **Requiere** cambiar *Settings → Pages → Source* a **GitHub Actions**.
- **Espejo vs enlace real**: la principal de una noticia fusionada podía ser BoF por el
  espejo de Google (`news.google.com/rss/articles/…`, redirección opaca que caduca). Si
  otro medio trae la misma noticia con enlace directo, ahora esa versión pasa a ser la
  principal (`_promote`) y BoF queda en "también en". La fusión vive en `merge_items()`.
- **Extractos sucios**: Drapers publica "Drapers <titular> <entradilla>" y el panel y la
  cápsula empezaban leyendo el nombre del medio. `strip_lead()` quita del inicio del
  extracto el nombre del medio, su etiqueta corta y el titular repetido.
- AGENTS.md puesto al día (el stack real incluye ffmpeg/Pillow/edge-tts en la cápsula) y
  sin la mención a Badabun: es un proyecto personal.

## 2026-11-06 · medios de México y Latinoamérica

Objetivo del usuario: que el radar cubra la moda de México y LatAm, no solo la internacional.

- **Cómo se probaron**: desde el contenedor de trabajo no hay salida a esos sitios, así que
  se creó el workflow manual *Probar fuentes* (`--check --muestra N`), que prueba desde las
  IP de GitHub —las mismas que usa el radar— y enseña titulares de ejemplo. 41 URLs de
  26 medios; 18 respondieron.
- **Entraron 13**: Vogue México, GQ México, Marie Claire México, Para Ti (AR), El Financiero,
  El Economista, Merca2.0, Perú Retail, Textiles Panamericanos, Modaes y FashionNetwork
  España (por Google News), y dos espejos por tema: *Pasarelas MX* (Fashion Week México) y
  *Moda en Tijuana*.
- **Descartadas**: Elle México, Quién, Expansión, Forbes México, El Economista/empresas
  (403); Harper's Bazaar México y FashionUnited (404, sin RSS); Glamour México (último
  artículo de mayo); Fahrenheit (SSL), América Retail (522), Revista Ya (reset), Inexmoda
  (no es XML), Fucsia (1 sola nota), InformaBTL (6 notas, casi nada de moda).
- **Revistas locales**: el filtro estricto de consumo solo dejaba negocio/retail/fichajes y
  se perdía justo lo interesante (diseñadores mexicanos, desfiles). Campo `local`: también
  aceptan pasarela, diseño y calzado. Las guías de estilo siguen fuera (NOISE_RE en español:
  "cómo llevar", "guía de estilo", "9 looks…", "Protegido:", Buen Fin...).
- **Espejos por tema** (`aggregator`): Google News mezcla medios y recortamos el " - Medio"
  del titular, así que se lee el `<source>` del ítem y la tarjeta dice "Publicado por …".
- Palabras clave: plurales en español ("diseñadores" no casaba con "diseñador"), anclas de
  moda en español para generalistas (ropa, prendas, textil, Shein, Zara, Inditex...).
- Panel: botón **México y LatAm** (regiones mx, latam, ar, co, cl, pe...).
- **Ajuste tras la primera edición** (199 noticias, 58 en español): Vogue México metía 9 guías
  de compra como "calzado" y notas de Vogue Italia en italiano; GQ México, un celular en
  retail ("flagship"). Calzado sale de las secciones aceptadas para revistas locales, más
  ruido en español ("para llevar", "ideas de", "más elegantes", "por 249 pesos",
  smartphone...), detector de italiano en fuentes `es` y fuera titulares de espejo de menos
  de 20 caracteres. Contra la edición real: salen 15 notas, las 15 eran ruido.

## 2026-11-06 · segunda cápsula: México y LatAm

- `capsule.py --edicion latam`: filtra noticias de medios de la región (mismas regiones que
  el botón del panel) más las internacionales cuyo titular nombra México/LatAm. Pesa más
  pasarela y diseño (`CAT_BONUS_LATAM`). Sale `AAAA-MM-DD-latam.mp4` + portada +
  `index-latam.json`; etiqueta "MX · LATAM" junto a la marca y portada/cierre propios.
  Con menos de 3 candidatas sale sin error y sin vídeo.
- La rotación local y la del Release van por edición (antes `*.mp4` habría mezclado las dos).
- Fecha del vídeo = fecha de la edición, no `datetime.now()` (si se montaba a mano después
  de las 4 pm de Tijuana el panel no lo encontraba). `gradient_canvas` con sha1 en vez de
  `hash()`.
- Notas en español: la plantilla ya no las manda a traducir. Enlaces de Google News: no se
  busca og:image en ellos (devolvería el logo de Google) → fondo de marca.
- Créditos de foto al inicio del extracto (Merca2.0: "FOTO: LAURA ISLAS …", "Bigstock.")
  se quitan en `strip_lead`.
- Kicker con espaciado según el ancho real de cada letra ("MÉXICO" salía "MÉXI CO").

## 2026-11-06 · Tijuana en la cápsula, fotos y créditos

Pedido del usuario: que salgan las notas de Tijuana; si no hay foto, una relacionada de
otro sitio; y **los créditos de foto se quedan** ("al final es darle crédito al fotógrafo").

- Revertida la limpieza de créditos de foto en los extractos (`CREDIT_RX` fuera).
- `enlaces.py`: descifra `news.google.com/rss/articles/…` → URL real (formato antiguo en
  base64; el nuevo `AU_yqL…` con la firma de la página + `batchexecute`, como la web de
  Google News). Luego lee og:image y og:description del artículo. Hasta 40 enlaces nuevos
  por edición, primero las búsquedas por tema. Caché de 1.500 entradas; los fallos se
  reintentan a los 2 días. Si Google lo cambia, falla en silencio y todo sigue como antes.
- Campo `via` (el medio real en las búsquedas por tema): el panel lo pone en la etiqueta
  ("Tijuana · El Imparcial") y la cápsula lo usa como "Fuente:".
- Cápsula: si no hay foto usable, busca en Openverse por lugar + tema ("fashion designer
  Tijuana", "catrina"…), sin repetir foto, y pinta "Foto: autor · licencia" bajo la fuente.
- Cápsula LatAm: hasta 2 notas de Tijuana/Baja California garantizadas, sin repetir el mismo
  evento (dos titulares con ≥2 palabras significativas en común).
- Primera edición con esto: 40 enlaces de Google resueltos (de 45 de espejo quedan 4 con
  enlace de Google). La cápsula LatAm salió con El Trompo (Tijuana) y DAFTA en Volvo
  Fashion Week, ambas con la foto del artículo. Openverse no hizo falta ese día.
- Codificación: Uniradio sirve latin-1 y se leía como UTF-8 ("Edicin reuni"). `decode_html`
  usa el charset de la cabecera o del `<meta>`, y si no, UTF-8 → cp1252.
