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
