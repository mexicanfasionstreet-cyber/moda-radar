# Proyecto: moda-radar

## Qué es
Agregador diario de noticias de la industria de la moda. Descarga 32 medios
especializados, elimina duplicados, agrupa por tema y publica un panel web estático
más un resumen en Markdown. Para uso personal de Badabun.

## Stack
- Python 3.12 **solo biblioteca estándar** (sin pip, sin claves API, sin coste).
- GitHub Actions (cron diario) + GitHub Pages (publicación del panel).

## Estructura
- `aggregate.py`  motor: descarga → limpia → deduplica → clasifica → renderiza.
- `ui.py`         CSS, JS y plantilla del panel.
- `sources.json`  catálogo de fuentes (verificadas el 2026-11-05).
- `docs/`         salida publicada: `index.html` + `data/*.json`.
- `digests/`      un Markdown por día.
- `memoria/`      bitácora fechada de decisiones y fallos.

## Comandos
```powershell
.\run.cmd              # generar panel y digest
.\run.cmd --check      # validar que las fuentes responden
.\run.cmd --days 7     # cambiar la ventana de días
```

## Reglas del proyecto
- No añadir dependencias externas: el script debe correr en un runner limpio sin `pip install`.
- Toda fuente nueva se valida con `--check` antes de entrar en `sources.json`.
- `docs/index.html` es generado: nunca editarlo a mano, se sobrescribe cada día.
- Los umbrales de deduplicación y las palabras clave se cambian en `aggregate.py`, no en la salida.

## Estado actual
Funcionando en local (137 noticias, 30/32 fuentes en la última pasada).
Pendiente: crear el repo en GitHub, activar Pages en `/docs` y el permiso de escritura
de Actions. Hypebeast y Textile World fallan de forma intermitente por límite de IP.
