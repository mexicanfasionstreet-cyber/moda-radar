# Publicar en YouTube e Instagram

El robot genera seis cápsulas al día. Esta parte las sube sola: **YouTube Shorts** y
**Stories de Instagram**. Si no hay credenciales, se salta la red y todo lo demás sigue
funcionando.

## Cuándo publica

- **Solo en las ejecuciones programadas** (07:00, 13:00 y 19:00 de Ciudad de México).
- En una ejecución manual hay que marcar la casilla **"Publicar también en YouTube e
  Instagram"** en *Run workflow*.
- Un push normal (cambio de código) genera las cápsulas pero **no publica**: así una
  prueba no se te va a las redes.

Cada red publica la edición general y la de México/LatAm: son **6 vídeos al día por red**.
Si una cápsula ya se publicó en las últimas 20 horas, se salta (registro en
`docs/videos/publicadas.json`).

## YouTube (empezar por aquí: es el único sin revisión)

1. Entra en https://console.cloud.google.com/ y crea un proyecto.
2. **APIs y servicios → Biblioteca** → busca *YouTube Data API v3* → **Habilitar**.
3. **APIs y servicios → Pantalla de consentimiento OAuth**: tipo *Externo*, pon nombre y
   correo. En *Usuarios de prueba*, añade tu cuenta de Google (la del canal).
4. **Credenciales → Crear credenciales → ID de cliente OAuth** → tipo de aplicación
   **"TVs and Limited Input devices"**. Apunta el **client ID** y el **client secret**.
5. En tu PC, con esos dos datos:

```powershell
$env:YT_CLIENT_ID = "tu-client-id"
$env:YT_CLIENT_SECRET = "tu-client-secret"
python herramientas/token-youtube.py
```

Te dará un código para escribir en `google.com/device` desde el móvil. Al autorizar
imprime el **refresh token**.

6. En GitHub: **Settings → Secrets and variables → Actions → New repository secret**,
   tres secretos:

| Secreto | Valor |
|---|---|
| `YT_CLIENT_ID` | el client ID |
| `YT_CLIENT_SECRET` | el client secret |
| `YT_REFRESH_TOKEN` | el que imprimió el script |

**Avisos importantes**

- Con la app en modo *Testing*, Google **caduca el refresh token cada 7 días**. Si te
  pasa, repite el paso 5 y actualiza el secreto. Para que no caduque, publica la app
  (botón *Publicar app*); el aviso de "app no verificada" solo sale al autorizar.
- La cuota de la API es de 10.000 unidades al día y **cada subida gasta 1.600**: las seis
  cápsulas diarias caben (9.600) pero sin margen. Si ves `quotaExceeded`, baja el número
  de publicaciones.
- Un canal nuevo suele tener **límite de subidas diarias** (a veces 1 o 2). YouTube
  responde `uploadLimitExceeded`; se resuelve subiendo menos cantidad durante unas semanas.

## Instagram Stories

Requiere cuenta **profesional** (Business o Creator) y una página de Facebook vinculada.

1. En https://developers.facebook.com/ crea una app de tipo *Business*.
2. Añade el producto **Instagram** y solicita los permisos `instagram_basic`,
   `instagram_content_publish` y `pages_show_list`.
3. En el *Explorador de Graph API*, consigue el **IG User ID** de tu cuenta y un **token
   de acceso de larga duración** (60 días).
4. Guarda dos secretos: `IG_USER_ID` y `IG_TOKEN`.

**Lo que hay que saber de las Stories**

- Meta solo acepta vídeos de **3 a 60 segundos**, así que cada cápsula se parte en dos
  tarjetas de ~35 s (`publicar.py` las corta con ffmpeg).
- Una Story **no lleva pie de foto ni enlace**: todo lo que quieras comunicar tiene que
  estar dentro del vídeo. Los enlaces del `-textos.txt` no sirven aquí; sí para YouTube.
- Meta no acepta subida directa: descarga el vídeo de una URL pública. Por eso el script
  sube cada trozo al Release `capsulas`, publica y **lo borra** al terminar.
- El token caduca a los 60 días. Cuando falle, genera otro y actualiza `IG_TOKEN`.

## Probar sin publicar

```powershell
python publicar.py --franja noche --dry-run
```

Muestra el título, la descripción y cuántas tarjetas saldrían, sin tocar ninguna red.

## Dónde queda el registro

`docs/videos/publicadas.json`: qué se publicó y cuándo. Es lo que evita duplicados si una
ejecución se repite. Si algo se publica mal, borra la entrada y vuelve a lanzar.
