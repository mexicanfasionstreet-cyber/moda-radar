# Proyecto: moda-radar

## Qué es
Radar diario de noticias de la industria de la moda. Descarga 45 medios
(32 internacionales, 13 de México/LatAm y en español), elimina duplicados, agrupa por tema y publica un panel web estático,
un resumen en Markdown, un corpus acumulado de noticias y **seis cápsulas al día** en
vídeo: tres franjas (mañana, mediodía, noche) × dos ediciones (general y México/LatAm).
Cada cápsula lleva su archivo `-textos.txt` con título, descripción y hashtags para
publicarla a mano.
Proyecto personal.

## Stack
- `aggregate.py` y `ui.py`: Python 3.12 **solo biblioteca estándar** (sin pip, sin claves).
- `capsule.py`: además necesita `ffmpeg`, `pillow` y `edge-tts` (los instala el workflow).
  La clave de IA (`LLM_API_KEY`) es opcional: sin ella el guion sale de una plantilla.
- GitHub Actions (cron diario) publica el panel en GitHub Pages (fuente: *GitHub Actions*)
  y archiva cada cápsula en el Release `capsulas`.

## Estructura
- `aggregate.py`  motor: descarga → limpia → deduplica → clasifica → renderiza.
- `capsule.py`    cápsula en vídeo: selección → guion → voz → montaje.
- `ui.py`         CSS, JS y plantilla del panel.
- `enlaces.py`    enlaces de Google News → artículo real (+ foto y entradilla), con caché.
- `sources.json`  catálogo de fuentes (verificadas el 2026-11-05).
- `docs/`         lo que se publica: `index.html` + `data/*.json` + `videos/index.json`.
- `datos/`        corpus acumulado (`noticias.jsonl` maestro + `noticias.csv`).
- `digests/`      un Markdown por día.
- `musica/`       pistas de fondo de la cápsula (CC0).
- `memoria/`      bitácora fechada de decisiones y fallos.

## Comandos
```powershell
.\run.cmd                   # generar panel, digest y corpus
.\run.cmd --check           # validar que las fuentes responden
.\run.cmd --days 7          # cambiar la ventana de días
python capsule.py --dry-run # ver el guion de la cápsula sin montar
python capsule.py --edicion latam --dry-run  # cápsula de México y LatAm
python capsule.py --franja noche --tts silent # montaje rápido con la franja de noche
```

## Reglas del proyecto
- `aggregate.py` y `ui.py` no llevan dependencias externas. Las dependencias de vídeo
  se quedan en `capsule.py`.
- Toda fuente nueva se valida antes de entrar en `sources.json`: desde GitHub con el workflow
  *Probar fuentes* (las IP de casa y de GitHub no ven lo mismo), o en local con `--check --muestra 3`.
- `docs/index.html` es generado: nunca editarlo a mano, se sobrescribe cada día.
- Los umbrales de deduplicación y las palabras clave se cambian en `aggregate.py`, no en la salida.
- Los vídeos (`docs/videos/*.mp4` y portadas) **no se commitean**: el historial de Git
  crecería ~1,4 GB al año. Viven en el Release `capsulas`; Pages publica el del día.
- `datos/noticias.jsonl` es append-only: nunca reescribirlo.

## Estado actual
En producción en https://mexicanfasionstreet-cyber.github.io/moda-radar/
(~140 noticias/día; Hypebeast bloquea las IP de los runners).
Medios de México y LatAm desde el 2026-11-06 (botón "México y LatAm" en el panel).
BoF y Textile World entran por espejo (Google/Bing News) cuando bloquean al robot.
Tres franjas desde el 2026-11-06: 07:00, 13:00 y 19:00 CDMX (13:00, 19:00 y 01:00 UTC).
El panel enlaza la cápsula más reciente del día y su `-textos.txt`.
