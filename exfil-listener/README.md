# Exfil Listener

Servidor HTTP (FastAPI) que simula la infraestructura de un atacante externo: recibe y registra cualquier dato que los escenarios de exfiltración le envíen, tal y como haría un servidor C2 tras un robo de datos exitoso.

## Archivos

| Archivo | Contenido |
|---|---|
| `app.py` | Lógica del servidor: rutas FastAPI, persistencia en `collected.log`. |
| `static/dashboard.html` | Panel web servido en `/` (HTML + CSS + JS, sin dependencias externas). |
| `collected.log` | Generado en tiempo de ejecución; una línea JSON por evento recibido. |

## Rutas

| Método | Ruta | Función |
|---|---|---|
| `GET` | `/` | Panel web con lo capturado (ver abajo). |
| `POST` | `/collect` | Recibe cualquier JSON y lo registra. Es el endpoint al que apuntan los ataques. |
| `GET` | `/api/events` | Lista los eventos capturados (más reciente primero) en JSON crudo. |
| `DELETE` | `/api/events` | Vacía el historial (memoria + `collected.log`). |
| `GET` | `/api/health` | Healthcheck simple, incluye el nº de eventos capturados. |

## Panel web

Al abrir `http://127.0.0.1:8888` se muestra una lista de los eventos capturados,
de más reciente a más antiguo, con:

- Marca de tiempo e IP de origen.
- Una etiqueta automática: **`BACKDOOR: ...`** (rojo) si el payload incluye la clave
  `leaked_via` o **`EXFILTRADO`** (ámbar) en cualquier
  otro caso.
- El payload completo en JSON, plegado por defecto.

Se auto-actualiza cada 2 segundos consultando `/api/events`; el botón **"Vaciar
log"** llama a `DELETE /api/events` para reiniciar el historial entre pruebas.
