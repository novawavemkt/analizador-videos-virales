"""
Backend local del Analizador de Videos Virales (portable).

Arranca con: uvicorn main:app --reload --port 8000

Expone una API REST muy simple que el frontend de React consume:
  POST /api/videos           -> crea un analisis nuevo (procesa en background)
  GET  /api/videos           -> lista el historial
  GET  /api/videos/{id}      -> estado + resultado de un analisis
  GET  /api/videos/{id}/frames/{frame_id} -> imagen de un fotograma
"""

import os
import threading

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import init_db, get_connection
from pipeline import process_video, reanalyze_video

app = FastAPI(title="Analizador de Videos Virales")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    if not os.environ.get("OPENAI_API_KEY"):
        print("AVISO: falta OPENAI_API_KEY en el entorno (ver .env.example).")
    init_db()


class CreateVideoRequest(BaseModel):
    url: str
    notas_manuales: str | None = None


class ReanalyzeRequest(BaseModel):
    notas_manuales: str | None = None


@app.post("/api/videos")
def create_video(body: CreateVideoRequest):
    url = body.url.strip()
    if not url.startswith("http"):
        raise HTTPException(400, "URL invalida.")

    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO videos (url, status, notas_manuales) VALUES (?, 'pending', ?)",
        (url, body.notas_manuales),
    )
    video_id = cur.lastrowid
    conn.commit()
    conn.close()

    thread = threading.Thread(
        target=process_video, args=(video_id, url, body.notas_manuales), daemon=True
    )
    thread.start()

    return {"id": video_id}


@app.post("/api/videos/{video_id}/reanalyze")
def reanalyze(video_id: int, body: ReanalyzeRequest):
    conn = get_connection()
    video = conn.execute("SELECT url FROM videos WHERE id = ?", (video_id,)).fetchone()
    conn.close()
    if not video:
        raise HTTPException(404, "No encontrado.")

    thread = threading.Thread(
        target=reanalyze_video, args=(video_id, video["url"], body.notas_manuales), daemon=True
    )
    thread.start()

    return {"ok": True}


@app.get("/api/videos")
def list_videos():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, url, platform, autor, status, duration_seconds, view_count, like_count,
               hook, formato, nicho, awareness_overall, puntuacion_media, created_at
        FROM videos ORDER BY created_at DESC LIMIT 200
        """
    ).fetchall()
    conn.close()
    return {"videos": [dict(r) for r in rows]}


@app.get("/api/videos/{video_id}")
def get_video(video_id: int):
    conn = get_connection()
    video = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
    if not video:
        conn.close()
        raise HTTPException(404, "No encontrado.")

    segments = conn.execute(
        """
        SELECT id, start_seconds, end_seconds, text, awareness_stage
        FROM video_segments WHERE video_id = ? ORDER BY ord ASC
        """,
        (video_id,),
    ).fetchall()

    frames = conn.execute(
        "SELECT id, timestamp_seconds FROM video_frames WHERE video_id = ? ORDER BY timestamp_seconds ASC",
        (video_id,),
    ).fetchall()
    conn.close()

    return {
        "video": dict(video),
        "segments": [dict(s) for s in segments],
        "frames": [dict(f) for f in frames],
    }


@app.get("/api/videos/{video_id}/frames/{frame_id}")
def get_frame(video_id: int, frame_id: int):
    conn = get_connection()
    frame = conn.execute(
        "SELECT image_bytes, content_type FROM video_frames WHERE id = ? AND video_id = ?",
        (frame_id, video_id),
    ).fetchone()
    conn.close()
    if not frame:
        raise HTTPException(404, "No encontrado.")
    return Response(content=frame["image_bytes"], media_type=frame["content_type"])
