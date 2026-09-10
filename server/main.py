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

import json

from db import init_db, get_connection
from pipeline import process_video, reanalyze_video
import audit_sheets
import audit_parser
from audit_report import render_report

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
               hook, formato, nicho, awareness_overall, puntuacion_media,
               filtro_angulo_pasa, filtro_avatar_pasa, potencial_viral, created_at
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


class ClientProfileRequest(BaseModel):
    angulo: str | None = None
    avatar: str | None = None
    posicionamiento: str | None = None


@app.get("/api/clients/{autor}")
def get_client_profile_endpoint(autor: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT autor, angulo, avatar, posicionamiento, updated_at FROM client_profiles WHERE autor = ?",
        (autor,),
    ).fetchone()
    conn.close()
    if not row:
        return {"autor": autor, "angulo": None, "avatar": None, "posicionamiento": None, "updated_at": None}
    return dict(row)


@app.put("/api/clients/{autor}")
def save_client_profile(autor: str, body: ClientProfileRequest):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO client_profiles (autor, angulo, avatar, posicionamiento, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(autor) DO UPDATE SET
            angulo = excluded.angulo,
            avatar = excluded.avatar,
            posicionamiento = excluded.posicionamiento,
            updated_at = datetime('now')
        """,
        (autor, body.angulo, body.avatar, body.posicionamiento),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Feature 2: informes de auditoria desde Google Sheets
# ---------------------------------------------------------------------------

class CreateAuditRequest(BaseModel):
    sheet_url: str


def _build_audit_from_sheet(sheet_url: str) -> dict:
    try:
        sheets = audit_sheets.read_sheet(sheet_url)
    except FileNotFoundError as e:
        raise HTTPException(500, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # errores de la API de Google (permisos, red...)
        raise HTTPException(502, f"No se pudo leer el Google Sheet: {e}")
    return audit_parser.parse_workbook(sheets)


@app.post("/api/audits")
def create_audit(body: CreateAuditRequest):
    data = _build_audit_from_sheet(body.sheet_url)
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO audit_reports (sheet_url, cliente, data_json) VALUES (?, ?, ?)",
        (body.sheet_url.strip(), data.get("cliente"), json.dumps(data, ensure_ascii=False)),
    )
    audit_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"id": audit_id, "cliente": data.get("cliente")}


@app.post("/api/audits/{audit_id}/refresh")
def refresh_audit(audit_id: int):
    conn = get_connection()
    row = conn.execute("SELECT sheet_url FROM audit_reports WHERE id = ?", (audit_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "No encontrado.")
    conn.close()

    data = _build_audit_from_sheet(row["sheet_url"])
    conn = get_connection()
    conn.execute(
        "UPDATE audit_reports SET cliente = ?, data_json = ?, updated_at = datetime('now') WHERE id = ?",
        (data.get("cliente"), json.dumps(data, ensure_ascii=False), audit_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "cliente": data.get("cliente")}


@app.get("/api/audits")
def list_audits():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, cliente, sheet_url, created_at, updated_at FROM audit_reports ORDER BY created_at DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return {"audits": [dict(r) for r in rows]}


@app.get("/api/audits/{audit_id}")
def get_audit(audit_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM audit_reports WHERE id = ?", (audit_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "No encontrado.")
    return {
        "id": row["id"],
        "cliente": row["cliente"],
        "sheet_url": row["sheet_url"],
        "data": json.loads(row["data_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@app.get("/api/audits/{audit_id}/report")
def get_audit_report(audit_id: int):
    conn = get_connection()
    row = conn.execute("SELECT data_json FROM audit_reports WHERE id = ?", (audit_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "No encontrado.")
    html = render_report(json.loads(row["data_json"]))
    return Response(content=html, media_type="text/html; charset=utf-8")
