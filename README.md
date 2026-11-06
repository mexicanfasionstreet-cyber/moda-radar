# Moda Radar

Radar diario de noticias de la industria de la moda. Cada día descarga 45 medios
(32 internacionales y 13 de México, Latinoamérica y prensa especializada en español), elimina duplicados, agrupa las noticias por tema y publica un panel
web + un resumen en Markdown. Se ejecuta solo en GitHub Actions: **no necesita
servidor, ni claves API, ni pagar nada**.

- Panel: `docs/index.html` (se publica como web con GitHub Pages)
- **Cápsula diaria en vídeo** (vertical 9:16, ~60 s): la del día en el panel; el archivo
  completo en el Release [`capsulas`](../../releases/tag/capsulas)
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
off en español. Se ve desde el botón **"Ver la cápsula del día"** del panel y queda
archivado en el Release `capsulas` del repo (se conservan las últimas 60).

**Cómo funciona** (`capsule.py`, cuatro pasos):

1. **Selección** — noticias con imagen, procurando variedad de secciones. Si el RSS no
   trae foto, se busca `og:image` en la propia página (WWD, por ejemplo, nunca la pone en
   el RSS).
2. **Guion** — un modelo escribe en español: gancho, dos frases por noticia (qué pasó y
   por qué importa) y cierre. Sin clave, la plantilla traduce titulares y entradillas al
   español con un traductor gratuito: correcto, pero más plano.
3. **Voz** — `edge-tts` (voces neuronales de Microsoft, gratis) genera el audio y se mide
   la duración real de cada frase.
4. **Montaje** — `ffmpeg` panea despacio sobre cada foto, el texto queda fijo encima y el
   audio manda el ritmo de cada plano. Duración típica: 55-65 s.

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
- El vídeo **no** se guarda en el historial de Git (pesa ~3-4 MB al día y el repo
  crecería más de 1 GB al año). Se publica en Pages el del día y se archiva en el Release
  `capsulas`, que borra solo las más antiguas.
- Si una noticia no tiene imagen, se usa la suya en miniatura como fondo desenfocado (o
  un degradado de marca). La selección prioriza siempre noticias con foto real.

## Música de fondo

La cápsula lleva una pista instrumental al ~30 % del volumen de la voz (−14 dB), con
entrada y salida suaves y en bucle si es más corta que el vídeo.

- **Cambiar la pista**: deja tu mp3 en `musica/fondo.mp3`. Cualquier duración o formato
  vale; el volumen se ajusta solo midiendo la pista.
- **Quitar la música** en una ejecución: `python capsule.py --sin-musica`.
- **Usar otra pista concreta**: `python capsule.py --music musica/otra.mp3`.

Las tres pistas incluidas son **CC0** (dominio público, sin atribución) descargadas de
Freesound vía Openverse: `fondo.mp3` (uplifting, 2:40) y dos alternativas de 20 s para
bucle. Sustitúyelas por las que te gusten: al ser música de fondo no hace falta declarar
nada, pero si usas una pista con copyright sí necesitarás licencia.

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

Repo → **Settings → Pages** → *Build and deployment* → *Source*: **GitHub Actions**.

(No hace falta elegir rama: el propio workflow publica la carpeta `docs/` al terminar
cada edición, con el vídeo del día incluido.)

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
.\run.cmd --check         # solo comprueba que las fuentes responden
```

Abre `docs/index.html` con doble clic: el panel funciona sin servidor.

## Medios de México y Latinoamérica

Además de la cápsula general, cada día sale una **cápsula de México y LatAm**
(`AAAA-MM-DD-latam.mp4`, botón "Cápsula México y LatAm" en el panel). Usa las noticias
de medios de la región y las de medios internacionales cuyo titular habla de México o
Latinoamérica. Si un día hay menos de 3, no se monta (no es un error). Se genera a mano con
`python capsule.py --edicion latam`.

El botón **"México y LatAm"** del panel deja solo las noticias de la región.

| Tipo | Medios | Qué entra |
|---|---|---|
| Revistas | Vogue México, GQ México, Marie Claire México, Para Ti (AR) | Negocio, retail, fichajes y, por ser locales, también pasarela, diseño y calzado. Fuera guías de estilo y celebridades. |
| Escena local | Pasarelas MX, Moda en Tijuana | Espejos de Google News por tema: noticias de muchos medios; la tarjeta dice cuál la publicó. |
| Negocio | El Financiero, El Economista, Merca2.0, Perú Retail | Solo si el titular habla de moda, ropa, textil, belleza, Shein, Zara… |
| Industria | Textiles Panamericanos, Modaes, FashionNetwork España | Todo. Modaes y FashionNetwork entran por Google News (no tienen RSS abierto). |

Probados y descartados el 2026-11-06: Elle México, Quién, Expansión, Forbes México e
Inexmoda (bloquean robots), Harper's Bazaar México y FashionUnited (sin RSS), Glamour
México (feed sin actualizar desde mayo), Fahrenheit, América Retail y Revista Ya (errores).

**Probar medios nuevos sin tocar el radar**: añádelos a `herramientas/fuentes-candidatas.json`
y lanza en GitHub **Actions → Probar fuentes → Run workflow**. El resultado dice qué URLs
responden, cuántas noticias traen, si tienen imagen y enseña titulares de ejemplo.

## Añadir o quitar fuentes

Edita `sources.json` y añade una línea:

```json
{"name": "Nombre del medio", "short": "Etiqueta", "url": "https://medio.com/feed/",
 "weight": 4.0, "lang": "en", "region": "us", "kind": "trade", "generic": false}
```

- `weight` (1-5): peso editorial. Más alto = aparece antes y gana en los empates.
- `kind`: `trade` (prensa especializada) o `consumer` (revista de consumo).
- `generic`: `true` para medios generalistas: solo entra lo que menciona moda en el titular.
- `local`: `true` en revistas de México/LatAm: aportan también pasarela, diseño y calzado.
- `mirror`: `true` si la URL es un feed de Google News. `aggregator`: además es por tema
  (mezcla medios) y la tarjeta muestra "Publicado por …".

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
│   └── videos/             index.json (los mp4 se generan pero no se commitean)
├── digests/                un Markdown por día
├── memoria/                bitácora de decisiones y fallos
└── .github/workflows/      tarea programada diaria
```
