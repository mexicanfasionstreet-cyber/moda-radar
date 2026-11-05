# datos — el corpus

Aquí se acumula todo lo que recoge el radar. Es la base para construir cualquier cosa
encima: análisis, informes, contenido, un boletín, lo que sea.

| Archivo | Qué es |
|---|---|
| `noticias.jsonl` | Una noticia por línea, formato JSON. **Es el archivo maestro**: crece para siempre, nunca se reescribe, y no se repite una noticia aunque aparezca en varias ediciones. |
| `noticias.csv` | La misma información en tabla, con BOM para que Excel la abra bien. Se regenera entero desde el `.jsonl` en cada pasada. |

## Campos

| Campo | Ejemplo | Notas |
|---|---|---|
| `id` | `a1b2c3d4e5f6` | Hash corto del enlace. Estable entre ejecuciones: sirve como clave primaria. |
| `published` | `2026-11-05T18:16:30Z` | Fecha de publicación en UTC, ISO 8601. |
| `title` | `Pierpaolo Piccioli Exits Balenciaga` | Titular tal cual lo publica el medio. |
| `source` | `BoF` | Etiqueta corta del medio. |
| `section` | `personas` | Sección asignada: `negocio`, `retail`, `pasarela`, `sostenibilidad`, `belleza`, `movimientos` (`personas`), `cultura`, `diseno`, `calzado`, `industria`. |
| `lang` | `en` | Idioma original: `en`, `es`, `it`. |
| `link` | `https://wwd.com/...` | Enlace al artículo, sin parámetros de seguimiento. |
| `excerpt` | `Owner Kering will announce...` | Entradilla limpia (sin HTML). Puede venir vacía. |
| `image` | `https://...jpg` | Imagen de portada del artículo. Puede venir vacía. |
| `also` | `Drapers; Elle` | Otros medios que publicaron la misma noticia. Si viene vacío, el radar solo la vio en ese medio. |
| `mirror` | `true` / `false` | `true` = la noticia entró por el espejo (Google/Bing News) porque el medio bloqueaba al robot. Solo trae titular y enlace. |
| `weight` | `5.0` | Peso editorial del medio (1-5), útil para priorizar. |

## Cómo usarlo

**pandas**

```python
import pandas as pd
df = pd.read_json("datos/noticias.jsonl", lines=True)
df["published"] = pd.to_datetime(df["published"])
df.groupby([df["published"].dt.date, "source"]).size().unstack(fill_value=0)
```

**Excel**: abre `noticias.csv` con doble clic. Si los acentos salen raros, usa
*Datos → Obtener datos → Desde texto/CSV* y elige UTF-8.

**PowerShell** (contar por medio):

```powershell
Get-Content datos/noticias.jsonl | ForEach-Object { $_ | ConvertFrom-Json } |
  Group-Object source | Sort-Object Count -Descending | Select-Object -First 10
```

## Qué se puede construir encima

- **Tendencias**: agrupar por `section` y semana para ver qué tema crece.
- **Quién cubre qué**: `also` indica qué historias comparten los medios; los temas con
  más cobertura son los importantes del día.
- **Base para resúmenes con IA**: cada línea ya es un documento limpio con metadatos.
- **Archivo consultable**: 365 días × ~130 noticias ≈ 47.000 registros al año.

## Aviso

El archivo crece ~90 KB al día (~30 MB al año). Si algún día molesta, se rota por año
(`noticias-2026.jsonl`); hoy no hace falta.
