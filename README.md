# Moda Radar

Radar diario de noticias de la industria de la moda. Cada día descarga 32 medios
especializados, elimina duplicados, agrupa las noticias por tema y publica un panel
web + un resumen en Markdown. Se ejecuta solo en GitHub Actions: **no necesita
servidor, ni claves API, ni pagar nada**.

- Panel: `docs/index.html` (se publica como web con GitHub Pages)
- **Cápsula diaria en vídeo: `docs/videos/AAAA-MM-DD.mp4`** (vertical 9:16, ~45 s)
- Resumen diario: `digests/AAAA-MM-DD.md`
- **Corpus acumulado: `datos/noticias.jsonl` + `datos/noticias.csv`** ← la base de datos
- Datos de la edición: `docs/data/latest.json`

## Cómo funciona

1. **Descarga** los RSS de `sources.json` en paralelo (con reintentos).
2. **Limpia** el HTML de cada noticia, quita parámetros de seguimiento de las URLs y
   descarta anuncios de empleo, listículos y contenido de estilo de vida.
3. **Filtra** por ventana de días (4 por defecto).
4. **Fusiona duplicados**: la misma noticia en WWD y en BoF aparece una sola vez, con
   la etiqueta "también en". Reconoce la misma noticia por similitud de titular y por
   entidad + tipo de acontecimiento (resultados, fichajes, operaciones).
5. **Clasifica** en una sección: Negocio, Retail, Pasarela, Sostenibilidad, Belleza,
   Movimientos, Cultura, Diseño, Calzado o Industria.
6. **Genera** el panel HTML (autocontenido, sin dependencias), el digest Markdown y
   **añade las noticias nuevas al corpus acumulado** (`datos/`).

El corpus es la parte importante si quieres construir algo encima: crece para siempre,
no repite noticias y tiene campos limpios (medio, sección, idioma, fecha, enlace,
extracto, cobertura). Los detalles están en [`datos/README.md`](datos/README.md).

## La cápsula en vídeo

Después de actualizar el panel, el robot monta un vídeo vertical de ~45 s con las cinco
noticias más relevantes del día: imagen de cada artículo, titular en pantalla y voz en
off en español. El resultado queda en `docs/videos/` y se ve desde el botón
**"Ver la cápsula del día"** del panel.

**Cómo funciona** (`capsule.py`, cuatro pasos):

1. **Selección** — las noticias con mejor puntuación que tengan imagen descargable,
   procurando variedad de secciones.
2. **Guion** — un modelo escribe el texto en español: gancho, una frase por noticia y
   cierre. Si no hay clave, cae a una plantilla (más plana, y los titulares en inglés).
3. **Voz** — `edge-tts` (voces neuronales de Microsoft, gratis) genera el audio y se mide
   la duración real de cada frase.
4. **Montaje** — `ffmpeg` panea despacio sobre cada foto, el texto queda fijo encima y el
   audio manda el ritmo de cada plano.

**Activar el guion con IA** (recomendado, cuesta céntimos al mes):

1. Consigue una clave de [DeepSeek](https://platform.deepseek.com/api_keys) (o de OpenAI).
2. En el repo: **Settings → Secrets and variables → Actions → New repository secret**.
3. Nombre: `LLM_API_KEY`. Valor: tu clave. **Save**.
4. Opcional, en la pestaña *Variables*: `LLM_BASE_URL` (por defecto
   `https://api.deepseek.com/v1`), `LLM_MODEL` (por defecto `deepseek-chat`) y
   `CAPSULE_VOICE` (por defecto `es-MX-DaliaNeural`).

Sin clave el robot sigue generando la cápsula con la plantilla: no se rompe nada.

**Probarla en tu PC**

```powershell
.\run.cmd                          # actualiza los datos
python capsule.py --dry-run        # ver el guion sin montar nada
python capsule.py --tts silent     # montar el vídeo sin voz (rápido)
python capsule.py                  # vídeo completo con voz
```

**Límites que conviene saber**

- Las imágenes son del medio original. Al publicarlas en redes, cita la fuente (el vídeo
  ya lo hace en pantalla) y revisa las condiciones de cada medio antes de monetizar.
- El vídeo se guarda en el repo y en GitHub Pages: cada día pesa ~2-4 MB. Se conservan
  los últimos 10; el peso se acumula en el historial de Git.
- Si una noticia no tiene imagen, se dibuja un fondo de marca con el titular: se nota, así
  que la selección prioriza siempre noticias con foto.

Las revistas de consumo (Vogue, Harper's Bazaar, GQ, Elle...) solo entran cuando la
noticia es de industria (negocio, retail, sostenibilidad o fichajes). Las fuentes de
retail genérico (CNBC, Retail Dive, Retail Gazette) solo entran si el titular menciona
moda, belleza o textil.

## Puesta en marcha (10 minutos)

### 1. Crear el repositorio y subirlo

En GitHub, crea un repositorio vacío (público o privado) llamado `moda-radar`, sin
README ni licencia. Después, desde esta carpeta:

```powershell
git init
git add .
git commit -m "moda-radar: primera version"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/moda-radar.git
git push -u origin main
```

### 2. Activar GitHub Pages

Repo → **Settings → Pages** → *Source*: **Deploy from a branch** →
*Branch*: `main`, carpeta `/docs` → **Save**.

En 1-2 minutos el panel estará en `https://TU_USUARIO.github.io/moda-radar/`.

### 3. Activar el permiso de escritura

Repo → **Settings → Actions → General** → *Workflow permissions*:
**Read and write permissions** → **Save**.

Sin esto el robot no puede publicar la edición diaria.

### 4. Primera ejecución manual

Repo → **Actions** → *Actualizar radar* → **Run workflow**.

A partir de ahí corre solo todos los días a las 12:00 UTC (04:00 en Los Ángeles,
13:00 en Madrid). GitHub puede retrasarlo unos minutos si está saturado.

## Uso local (opcional, para probar antes de subir)

```powershell
.\run.cmd                 # genera el panel con la ventana por defecto
.\run.cmd --days 7        # ventana de 7 días
.\run.cmd --check         # solo comprueba que las 32 fuentes responden
```

Abre `docs/index.html` con doble clic: el panel funciona sin servidor.

## Añadir o quitar fuentes

Edita `sources.json` y añade una línea:

```json
{"name": "Nombre del medio", "short": "Etiqueta", "url": "https://medio.com/feed/",
 "weight": 4.0, "lang": "en", "region": "us", "kind": "trade", "generic": false}
```

- `weight` (1-5): peso editorial. Más alto = aparece antes y gana en los empates.
- `kind`: `trade` (prensa especializada) o `consumer` (revista de consumo).
- `generic`: `true` solo para medios de retail general que no son de moda.

Comprueba que la URL es un RSS válido antes de darla por buena:

```powershell
.\run.cmd --check
```

## Ajustes rápidos

| Qué quieres cambiar | Dónde |
|---|---|
| Hora de actualización | `.github/workflows/daily.yml`, línea `cron` (UTC) |
| Días de histórico en el panel | `--days 4` en el workflow |
| Secciones y palabras clave | `CATS` en `aggregate.py` |
| Colores y tipografía | `CSS` en `ui.py` |
| Máximo de noticias por medio | `MAX_PER_FEED` en `aggregate.py` |

## Limitaciones conocidas

- **Hypebeast** bloquea peticiones repetidas desde la misma IP (error 405). Si falla
  varios días seguidos, quítalo de `sources.json`: el resto del panel no se ve afectado.
- **Textile World** a veces responde con un bucle de redirección desde algunas IP.
- Los medios de pago (Vogue Business, Sourcing Journal, Business of Fashion completo)
  no ofrecen RSS abierto: entran solo los titulares y extractos que publican.
- La fusión de duplicados entiende inglés, español e italiano por entidad y palabra
  clave, pero no traduce: dos titulares muy distintos sobre lo mismo pueden quedar
  separados.
- Las imágenes se cargan desde el medio original (`<img src>` directo). Si un medio
  cambia la URL, la tarjeta cae al monograma de la fuente.

## Estructura

```
moda-radar/
├── aggregate.py            motor: descarga, limpia, deduplica, clasifica y renderiza
├── capsule.py              genera la cápsula en vídeo (guion, voz y montaje)
├── ui.py                   estilos y plantilla del panel
├── sources.json            catálogo de fuentes verificadas
├── run.cmd                 ejecución local en Windows
├── datos/
│   ├── noticias.jsonl      CORPUS: una noticia por línea, crece para siempre
│   ├── noticias.csv        el mismo corpus en tabla (Excel)
│   └── README.md           diccionario de campos y ejemplos de uso
├── docs/
│   ├── index.html          panel (generado, se sobrescribe cada día)
│   ├── data/               latest.json + un JSON por día (archivo)
│   └── videos/             cápsulas mp4 + portada + index.json
├── digests/                un Markdown por día
├── memoria/                bitácora de decisiones y fallos
└── .github/workflows/      tarea programada diaria
```
