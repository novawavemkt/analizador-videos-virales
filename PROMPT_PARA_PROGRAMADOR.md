# Prompt para Claude Code — Analizador de Vídeos Virales (Nova Wave)

> Copia todo este documento y pégalo como primer mensaje a Claude Code en tu
> ordenador. Describe el estado actual del proyecto con detalle técnico para
> que puedas orientarte rápido, tanto si vas a seguir tal cual como si vas a
> cambiar cosas (arquitectura, stack, lo que sea).

---

## Contexto

Repo existente, ya funcionando: **https://github.com/novawavemkt/analizador-videos-virales**

```bash
git clone https://github.com/novawavemkt/analizador-videos-virales
cd analizador-videos-virales
```

Es una app **100% local** (sin servidor central, sin cuentas de usuario) que:
recibe un link de un reel de TikTok/Instagram, lo descarga, transcribe el
audio, y genera un informe de análisis de marketing/copywriting con IA
(nivel de consciencia del cliente, hook, estructura narrativa, puntuación,
recomendaciones...). Todo corre en el ordenador de quien la usa; cada
instalación usa su propia API key de OpenAI.

**El código puede y probablemente deba cambiar** — esto describe el estado
actual (qué se usa y por qué), no una arquitectura que haya que preservar a
toda costa.

---

## Arquitectura general

```
web/ (React + Vite, puerto 5173)  <--HTTP-->  server/ (FastAPI, puerto 8000)  -->  analizador.db (SQLite)
                                                     |
                                                     +--> yt-dlp / gallery-dl (descarga)
                                                     +--> ffmpeg (audio + fotogramas)
                                                     +--> OpenAI API (Whisper + GPT-4o-mini)
```

Dos procesos que hay que arrancar por separado (dos terminales), sin
orquestador ni Docker todavía:
```bash
# Terminal 1
cd server && uvicorn main:app --reload --port 8000

# Terminal 2
cd web && npm run dev
```

---

## Backend (`server/`)

- **Lenguaje/framework**: Python 3.10+, **FastAPI** (`main.py`) servido con
  **Uvicorn** (`uvicorn main:app --reload`).
- **Sin ORM**: acceso a SQLite directo con el módulo `sqlite3` de la
  librería estándar (`db.py`). Sin SQLAlchemy ni similar.
- **Sin frameworks de auth**: no hay login ni usuarios — es de un único
  operador por instalación.
- **Estructura de 3 archivos**:
  - `main.py` — endpoints REST (`/api/videos`, `/api/videos/{id}`,
    `/api/videos/{id}/reanalyze`, `/api/videos/{id}/frames/{frame_id}`,
    `/api/clients/{autor}`). CORS abierto solo a `localhost:5173`.
  - `pipeline.py` — toda la lógica de negocio: descarga, extracción,
    transcripción, clasificación con IA. Se ejecuta en un `threading.Thread`
    daemon por vídeo (no hay cola de verdad, es concurrencia simple con
    threads de Python).
  - `db.py` — esquema SQL (`CREATE TABLE IF NOT EXISTS`) + una función
    `_migrate()` que añade columnas nuevas a bases de datos ya existentes
    con `ALTER TABLE` (migraciones manuales, sin Alembic).
- **Variables de entorno** (`server/.env`, cargado con `python-dotenv`):
  - `OPENAI_API_KEY` (obligatoria)
  - `COOKIES_FILE` / `COOKIES_FROM_BROWSER` (opcionales, ver abajo)

## Frontend (`web/`)

- **React 19 + TypeScript + Vite** (scaffold de `npm create vite -- --template react-ts`).
- **react-router-dom** para las 3 páginas: `Dashboard` (nuevo análisis),
  `VideoDetail` (resultado + regenerar + perfil de cliente), `History`
  (listado con filtros por pestañas).
- **react-markdown** para renderizar el informe (llega como texto markdown
  desde el backend).
- **CSS a mano** en un único `index.css` — sin Tailwind, sin librería de
  componentes (Material UI, shadcn, etc.). Tema oscuro fijo.
- **Sin gestor de estado global** (Redux/Zustand) — todo con `useState`/
  `useEffect` por página, llamando directo a `fetch` contra
  `http://localhost:8000` (cliente HTTP a mano en `src/api.ts`, sin axios ni
  react-query).
- **Polling, no websockets**: `VideoDetail` hace `setInterval` cada 2.5s
  mientras el vídeo está `pending`/`processing`, hasta que cambia a `done`/`error`.

## Base de datos

**SQLite**, un único archivo `server/analizador.db` (se crea solo al
arrancar, no se versiona en git). Tablas:

- `videos` — una fila por análisis: url, platform, autor (@cuenta extraída
  de metadatos), status (pending/processing/done/error), metadatos
  (duración/vistas/likes), campos de clasificación (hook, formato, nicho,
  awareness_overall), `informe_markdown` (el informe completo),
  `puntuacion_media`, `filtro_angulo_pasa`/`filtro_avatar_pasa`/
  `filtro_explicacion`, `notas_manuales`, `transcript`.
- `video_segments` — desglose del vídeo en tramos con timestamps, cada uno
  con su etapa de consciencia de Schwartz.
- `video_frames` — los fotogramas extraídos, guardados como `BLOB` (bytes)
  directamente en la BD, no en disco.
- `client_profiles` — perfil por `@autor` (ángulo/avatar/posicionamiento,
  metodología del Módulo 1-2 de Nova Wave), usado como "memoria" para
  evaluar todos los vídeos de esa cuenta contra el mismo perfil.

## Herramientas usadas por funcionalidad

| Funcionalidad | Herramienta | Notas |
|---|---|---|
| Descarga de vídeo + metadatos (duración/vistas/likes) | **yt-dlp** (primero) → **gallery-dl** (fallback automático si yt-dlp falla) | TikTok bloquea yt-dlp con cierta frecuencia; gallery-dl es un extractor mantenido de forma independiente que a veces funciona cuando yt-dlp no. Ver `get_metadata`/`download_video` vs `get_metadata_gallery_dl`/`download_video_gallery_dl` en `pipeline.py`. |
| Bloqueos que requieren sesión (login wall) | Cookies vía `--cookies <archivo>` (`COOKIES_FILE`) o `--cookies-from-browser` (`COOKIES_FROM_BROWSER`) | `COOKIES_FILE` es más fiable en Windows (evita el cifrado DPAPI de navegadores Chromium recientes). El archivo de cookies se exporta a mano con una extensión de navegador tipo "Get cookies.txt LOCALLY" — no se puede automatizar (cookies httpOnly, requiere sesión real del usuario). |
| Extraer audio del vídeo | **ffmpeg** (`-vn -acodec libmp3lame`) | Proceso externo, invocado por `subprocess`. |
| Extraer fotogramas | **ffmpeg** (`-ss <segundos> -frames:v 1`) | Solo 3 fotogramas fijos, en 0.5s/1.5s/3s (el hook). **No cubre el resto del vídeo** — limitación conocida, candidata a mejorar. |
| Transcripción de audio | **OpenAI Whisper API** (`whisper-1`, `response_format=verbose_json`) | Da texto + segmentos con timestamps. Corre en la nube de OpenAI, no localmente. |
| Texto en pantalla / OCR | **No implementado** | El modelo de clasificación "ve" los 3 fotogramas (es multimodal) pero no hay OCR dedicado ni se analiza texto en pantalla fuera de esos 3 fotogramas. |
| Clasificación + informe (hook, copy, producción, algoritmo, puntuación, recomendaciones, nivel de consciencia, filtro ángulo/avatar) | **OpenAI GPT-4o-mini**, `response_format={"type":"json_object"}` | Recibe: transcripción con timestamps, metadatos, métricas reales (vistas/likes), notas manuales, perfil de cliente (ángulo/avatar/posicionamiento), historial de análisis previos de la misma cuenta, y las 3 imágenes. Devuelve JSON con el informe completo en markdown + campos estructurados para la UI. El *system prompt* es el prompt maestro de Nova Wave (constante `MASTER_PROMPT` en `pipeline.py`) + un addendum técnico propio (`TECHNICAL_ADDENDUM`) que pide el JSON y añade la lógica del filtro de ángulo/avatar (Módulo 1-2) — el addendum NO debe tocar el contenido del prompt maestro, solo añadir instrucciones de formato de salida. |
| "Memoria" entre vídeos de un mismo cliente | Consulta SQL directa a `videos` filtrando por `autor`, extrayendo resumen + recomendaciones de los últimos 3 análisis (función `get_client_memory`) | No es una memoria vectorial ni embeddings — es texto plano de análisis previos metido en el prompt. |
| Filtro de ángulo/avatar (Módulo 1-2 Nova Wave) | Tabla `client_profiles` + instrucción en el prompt | El usuario rellena ángulo/avatar/posicionamiento una vez por cuenta desde la UI (`VideoDetail`), y se aplica a todos sus vídeos. |
| Regenerar análisis con notas nuevas | Mismo pipeline completo (`reanalyze_video` → `process_video`), vuelve a descargar y reprocesar | No cachea el vídeo original entre ejecuciones — cada regeneración descarga de nuevo. Candidato claro a optimizar si molesta. |

## Cómo se conecta todo (flujo end-to-end)

1. Usuario pega URL en el Dashboard → `POST /api/videos` → inserta fila
   `status=pending` en SQLite → lanza un thread en background → responde con
   el `id` al instante (no bloquea).
2. El thread (`process_video`): metadatos + descarga (yt-dlp, con fallback a
   gallery-dl) → extrae audio y 3 fotogramas (ffmpeg) → transcribe (Whisper)
   → clasifica (GPT-4o-mini, con memoria de cliente + perfil de
   ángulo/avatar si existen) → guarda todo en SQLite, borra los archivos
   temporales de vídeo/audio (solo persisten transcript + informe +
   fotogramas).
3. El frontend hace polling a `GET /api/videos/{id}` cada 2.5s hasta ver
   `status=done` (o `error`), y entonces renderiza el resultado completo.

## Limitaciones conocidas / candidatas a mejora

- Solo 3 fotogramas fijos al inicio del vídeo — no hay cobertura visual del
  resto ni OCR real.
- Concurrencia con `threading.Thread` sin límite ni cola — si se lanzan
  muchos análisis a la vez, no hay control de cuántos corren en paralelo.
- Reintentar/regenerar vuelve a descargar el vídeo desde cero (no hay caché).
- TikTok puede seguir bloqueando peticiones incluso con el fallback a
  gallery-dl si ambos extractores fallan a la vez (raro, pero posible).
- Sin tests automatizados todavía.
- El prompt maestro (`MASTER_PROMPT`) es contenido propio de Nova Wave
  (metodología de copywriting/consciencia del cliente) — no modificarlo sin
  que el equipo de Nova Wave lo apruebe; el `TECHNICAL_ADDENDUM` sí es
  código de la app y se puede tocar libremente.

## Setup rápido

Ver el `README.md` del repo para el paso a paso completo (requisitos,
instalación, variables de entorno). Resumen:

- Python 3.10+, Node 18+, ffmpeg, una API key propia de OpenAI con
  facturación activa.
- `pip install -r server/requirements.txt` + `cp server/.env.example
  server/.env` (rellenar `OPENAI_API_KEY`).
- `cd web && npm install`.
- Arrancar backend y frontend en dos terminales (ver arriba).
