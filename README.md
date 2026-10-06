# Risitas Bot

Bot de Discord con integracion de Twitch, MongoDB y una API HTTP privada para
el panel DarkOps. El proyecto esta preparado para ejecutarse como Web Service
gratuito en Render.

## Despliegue en Render

1. Crea un Blueprint nuevo en Render y conecta este repositorio.
2. Render detectara `render.yaml` y creara el Web Service gratuito.
3. Completa las variables marcadas como secretas o manuales. Puedes tomar sus
   nombres de `.env.example`; nunca subas tu archivo `.env`.
4. Despliega el servicio. Render proporciona automaticamente `PORT` y
   `RENDER_EXTERNAL_URL`.

El proceso escucha en `0.0.0.0:$PORT`. La API se inicia antes de la conexion a
Discord, por lo que Render puede comprobar el proceso durante el arranque. El
servicio se llama a si mismo mediante `RENDER_EXTERNAL_URL/keepalive` cada 14
minutos.

## Variables requeridas

- `DISCORD_TOKEN`
- `DEVELOPER_ID`
- `MONGODB_URI`
- `TWITCH_CLIENT_ID`
- `TWITCH_CLIENT_SECRET`

Los IDs de canales y roles dependen de las funciones que quieras habilitar.

## Registrar cumpleaños de otra persona

`/setcumpleaños usuario:@Persona dia:15 mes:8` registra o actualiza el cumpleaños
de la persona seleccionada en la misma colección de MongoDB que `/cumpleaños`.
Solo pueden ejecutarlo los administradores del servidor o el desarrollador
configurado en `DEVELOPER_ID`, incluso si este último no tiene rol de administrador.
La confirmación es privada y las fechas inválidas no se guardan.

## API

- `GET /health`: salud publica del proceso y estado de Discord.
- `GET /keepalive`: destino publico de la autollamada.
- `GET /api/v1/status`: estado detallado de Discord.
- `GET /api/v1/commands`: catalogo de comandos.
- `PATCH /api/v1/commands/{name}`: activa o desactiva un comando.
- `POST /api/v1/commands/sync`: sincroniza con Discord.
- `GET /api/v1/embeds/birthday`: vista previa de cumpleaños.
- `GET /api/v1/birthday/settings`: plantilla guardada, revisión y canales/roles disponibles.
- `PUT /api/v1/birthday/settings`: guarda `{ settings, revision }` en MongoDB.
- `POST /api/v1/birthday/preview`: renderiza `{ settings }` sin guardar ni enviar mensajes.

El editor está en DarkOps → Risitas · Discord → Cumpleaños. Requiere el permiso
`risitas` o acceso de administrador. La configuración persiste en `botdb.settings`
(documento `birthday`) y prevalece sobre los valores iniciales de las variables de
entorno. El bot lee esa plantilla para enviar felicitaciones, con la misma función
que genera la vista previa. Guardar no modifica mensajes ya enviados.

Se pueden editar mensaje, título, descripción, color, autor, pie, imagen, miniatura,
campos adicionales, canal, rol mencionado, notificaciones, hora y zona horaria.
El rol no se asigna automáticamente. El envío conserva la revisión horaria del bot:
se realiza durante la hora elegida, no necesariamente en el minuto cero.
Los límites se validan según la [documentación de Discord](https://docs.discord.com/developers/resources/message#embed-limits).
Una revisión desactualizada devuelve 409 y no sobrescribe los cambios ajenos.

Salvo `/`, `/health` y `/keepalive`, los endpoints requieren
`Authorization: Bearer <API_KEY>` o `X-API-Key: <API_KEY>`.

## Desarrollo local

Copia `.env.example` como `.env`, completa sus valores y ejecuta:

```bash
pip install -r requirements.txt
python main.py
```

Las pruebas no necesitan credenciales reales:

```bash
python -m unittest discover -s tests -v
```

El archivo `.env` esta excluido de Git.
