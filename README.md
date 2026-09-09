# Analizador de Vídeos Virales

Herramienta local (backend en Python + frontend en React) para analizar reels
de TikTok e Instagram: transcripción, nivel de conciencia del cliente (Eugene
Schwartz), nicho, formato narrativo, puntuación por ejes y un informe completo
listo para pegar en un reporte de cliente.

Corre 100% en tu propio ordenador. No hay servidor central ni cuentas: cada
persona que lo use pone su propia API key de OpenAI.

## Qué hace

Por cada link que pegues, la app:

1. Descarga el vídeo y saca sus metadatos (duración, vistas, likes) con `yt-dlp`.
2. Extrae el audio y 3 fotogramas clave con `ffmpeg`.
3. Transcribe el audio con timestamps (Whisper API de OpenAI).
4. Genera un informe completo (hook, copy y persuasión, producción, señales de
   algoritmo, puntuación, recomendaciones...) con GPT-4o, usando un nivel de
   detalle de consultor.
5. Clasifica el vídeo por nivel de conciencia de Eugene Schwartz — tanto una
   etiqueta general como un desglose por tramos de tiempo.
6. Guarda todo en una base de datos local (SQLite, un solo archivo) para que
   puedas filtrar el historial por plataforma, usuario, nicho, formato o
   etapa de conciencia.

También puedes añadir notas manuales a cada análisis (contexto, resultados
reales del cliente...) y regenerar el informe para que las integre.

## Requisitos previos

- **Python 3.10+** — https://www.python.org/downloads/
- **Node.js 18+** — https://nodejs.org
- **ffmpeg**:
  - Windows: `winget install Gyan.FFmpeg`
  - Mac: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`
- **Una API key de OpenAI** (tuya, no se comparte con nadie):
  1. Crea cuenta en https://platform.openai.com
  2. Añade un método de pago en https://platform.openai.com/settings/billing
     (el uso es de pago por consumo: Whisper son céntimos por minuto de
     audio, GPT-4o unos pocos céntimos por vídeo analizado)
  3. Genera una key en https://platform.openai.com/api-keys

## Instalación

Clona el repositorio y entra en la carpeta:

```bash
git clone <url-de-este-repo>
cd analizador-portable
```

### Backend

```bash
cd server
pip install -r requirements.txt
cp .env.example .env
```

Edita `server/.env` y pon tu API key:

```
OPENAI_API_KEY=tu-api-key-aqui
```

### Frontend

```bash
cd web
npm install
```

## Cómo arrancarlo

Necesitas **dos terminales abiertas a la vez**:

**Terminal 1 — backend:**
```bash
cd server
uvicorn main:app --reload --port 8000
```

**Terminal 2 — frontend:**
```bash
cd web
npm run dev
```

Abre `http://localhost:5173` en tu navegador. Pega un link de TikTok o
Instagram y dale a "Analizar".

## Estructura del proyecto

```
server/          Backend (FastAPI + SQLite)
  main.py        Endpoints de la API
  pipeline.py    Descarga, transcripcion y clasificacion (yt-dlp, ffmpeg, OpenAI)
  db.py          Esquema y conexion a SQLite
  analizador.db  Base de datos local (se crea sola, no se sube al repo)

web/             Frontend (React + Vite)
  src/pages/     Dashboard, detalle de video, historial
  src/api.ts     Cliente HTTP hacia el backend
```

## Notas

- Si un link falla al descargar ("Instagram sent an empty media response" o
  similar), suele ser porque el post requiere estar logueado o no es un
  vídeo (puede ser un carrusel de fotos).
- Los vídeos y audios descargados son temporales y se borran tras procesar
  cada uno — solo se guardan de forma permanente la transcripción, el
  informe y 3 fotogramas pequeños.
- **Nunca subas tu `server/.env`** (ya está en `.gitignore`) ni compartas tu
  API key con nadie — cada persona que use esta herramienta debe generar la suya.

## Licencia

MIT — ver [LICENSE](LICENSE).
