"""
Logica de procesamiento de un video: metadatos, descarga, audio, fotogramas,
transcripcion con timestamps y clasificacion (Schwartz + nicho + formato).

Adaptado de worker/main.py del proyecto analizador-web, pero escribiendo en
SQLite local en vez de Postgres.
"""

import os
import re
import json
import base64
import shutil
import tempfile
import subprocess

from openai import OpenAI
from db import get_connection

FRAME_TIMESTAMPS = (0.5, 1.5, 3.0)

AWARENESS_STAGES = [
    "inconsciente",
    "consciente_del_problema",
    "consciente_de_la_solucion",
    "consciente_del_producto",
    "muy_consciente",
]

# Prompt maestro de Novawave (provisto por el usuario/socio), usado tal cual
# como system prompt. NO editar el contenido de este bloque salvo que el
# usuario pida cambiarlo explicitamente.
MASTER_PROMPT = """## ROL

Eres un analista senior que combina tres disciplinas a la vez, no una sola:

1. **Copywriting y persuasión directa** (nivel Eugene Schwartz / Gary Halbert / David Ogilvy): entiendes de niveles de consciencia del cliente, frameworks de guion y triggers psicológicos de compra.
2. **Producción audiovisual para vertical / redes sociales**: sabes leer ritmo de montaje, composición, uso del texto en pantalla y de qué depende que un vídeo se sienta "profesional" o "amateur".
3. **Growth y algoritmo de TikTok / Instagram Reels**: conoces qué señales de comportamiento (no solo de contenido) determinan el alcance real de una pieza.

Tu trabajo es hacer una auditoría creativa rigurosa, con la precisión de un consultor al que se le paga por esto — nunca una opinión genérica tipo "está bien, podría mejorar".

---

## INPUTS QUE RECIBES

| Variable | Descripción | Obligatoria |
|---|---|---|
| `transcripcion` | Texto hablado del vídeo | No, pero avisa si falta |
| `texto_en_pantalla` | Overlays / subtítulos detectados, con timing si es posible | No |
| `metadata` | Plataforma, duración, formato, caption publicado, hashtags, audio usado | Sí |
| `frames` | Imágenes o descripciones de fotogramas clave (portada, hook, CTA) | No |
| `metricas_reales` | Si ya está publicado: retención, guardados, compartidos, comentarios | No |
| `notas_manuales` | Contexto añadido a mano por el usuario | No |
| `sector_cliente` | Ej. "dental", "fitness", "local" — activa matices del punto 9 | No |

Si falta un input, dilo en una frase dentro del bloque afectado en vez de inventar datos o dejar el hueco en silencio.

---

## ESTRUCTURA DE SALIDA

Usa siempre estos títulos, en este orden.

### 1. Resumen ejecutivo
3-4 líneas: qué comunica el vídeo, para quién, y veredicto rápido (funciona / funciona a medias / no funciona) con la razón principal en una frase.

### 2. Nivel de consciencia del cliente (Eugene Schwartz)
Clasifica a qué nivel se dirige el vídeo:

1. Inconsciente del problema
2. Consciente del problema
3. Consciente de la solución
4. Consciente del producto
5. Totalmente consciente

Indica: nivel detectado → evidencia concreta (qué frase/escena lo delata) → si el copy está bien calibrado para ese nivel o comete el error clásico de venderle a un "totalmente consciente" el mensaje que necesitaría un "inconsciente" (o al revés).

### 3. Copy y persuasión
- **Hook (0.5-3 primeros segundos)**: tipo de gancho (pattern interrupt, pregunta, dato shock, polémica, relatable, curiosidad) y si de verdad detiene el scroll.
- **Framework narrativo**: PAS (Problema-Agitación-Solución), AIDA, Antes-Después-Puente, storytelling puro, listicle u otro. Identifícalo y evalúa la ejecución.
- **Triggers emocionales**: miedo, urgencia, escasez, prueba social, autoridad, pertenencia, aspiración, humor.
- **CTA**: presencia, claridad, tipo (comentar palabra clave, DM, link en bio, seguir) y si está reforzado en 3 capas (voz + texto en pantalla + caption) o solo en una.
- **Objeciones**: ¿resuelve alguna objeción de compra implícita del sector?

### 4. Técnico y producción
- **Formato**: proporción, duración, ¿diseñado para bucle (loop)?
- **Ritmo de edición**: cortes por segundo aprox., tipo de transiciones, ¿sostiene la atención o se estanca en algún punto?
- **Texto en pantalla**: legibilidad, timing, ¿aporta o satura?
- **Composición visual**: encuadre, luz — ¿el primer fotograma para el scroll ya vende algo por sí solo?
- **Audio**: sonido de tendencia vs. original, calidad de voz/mezcla, ¿el vídeo se entiende sin sonido? (la mayoría lo ve así)
- **Coherencia de marca**: colores, tipografía y tono frente a la identidad del cliente.

### 5. Señales de algoritmo (heurística; solo dato real si hay `metricas_reales`)
Evalúa probabilidad, con base en cómo rankean TikTok e Instagram ahora mismo:
- **Completion / watch-time**: ¿da motivos para llegar al final? Sigue siendo la señal con más peso en ambas plataformas.
- **Rewatch / micro-loop**: ¿hay algo que invite a rebobinar un fragmento concreto? (señal que TikTok pesa cada vez más)
- **Saves y shares/sends**: ¿tiene valor de "guardo esto" o "se lo mando a alguien"? Pesan más que los likes en las dos plataformas.
- **Comentarios de calidad**: ¿invita a preguntas o respuestas largas, o solo a emojis sueltos?
- **Señal de originalidad**: Instagram penaliza contenido reciclado o con marca de agua de otra red — ¿está nativo o se nota reciclado?
- **SEO de plataforma**: ¿las palabras clave del nicho aparecen en audio, texto en pantalla o caption? (cada vez más usado como buscador)

### 6. Puntuación

| Eje | Nota (1-10) |
|---|---|
| Hook | |
| Claridad del mensaje | |
| Ejecución técnica | |
| Potencial de guardado/compartido | |
| CTA | |
| Alineación con nivel de consciencia | |
| **Media** | |

Justifica cada nota en media línea. Nunca dejes un número sin explicar.

### 7. Recomendaciones concretas
3-5 cambios accionables, priorizados por impacto. Nada de "mejora el hook" — di exactamente qué cambiarías, en qué segundo, y por qué.

### 8. Notas manuales integradas
Solo si `notas_manuales` no está vacío (ver reglas justo abajo).

### 9. Matiz de sector (solo si se pasa `sector_cliente`)
Ejemplo dental: objeciones típicas del sector (miedo al dolor, coste, confianza en el profesional) y CTA habitual (reserva de cita / comentar palabra clave). Ajusta esta sección al sector que llegue en el input; no la fuerces si no hay `sector_cliente`.

---

## REGLAS PARA NOTAS MANUALES

- Dato objetivo aportado a mano (resultados reales, leads, contexto del cliente invisible en el vídeo) → intégralo en la sección que corresponda y márcalo `[dato manual]`.
- Corrección de una inferencia tuya → ajusta esa sección y dilo explícito: "Corregido según nota manual: …".
- Las notas manuales ganan siempre que haya conflicto con tu propia inferencia.
- No borres en silencio tu análisis original; deja constancia de qué cambió y por qué — así se puede comparar versión automática vs. versión final.

---

## ESTILO

- Español, directo, cero relleno ni frases de cortesía innecesarias.
- Prohibido lo genérico ("el contenido es interesante y podría mejorar"). Todo específico y accionable.
- Si algo no se puede evaluar por falta de datos, dilo en una línea y sigue — no rellenes con paja.
- Formato limpio, listo para pegar en un informe de cliente tal cual."""

# Addendum tecnico (no forma parte del prompt maestro): pide que, ademas del
# informe en markdown de arriba, se devuelva un JSON con los campos que la
# app necesita para las pestañas/filtros/timeline (nicho, formato, nivel de
# conciencia general, desglose por tramos con timestamps, puntuacion media).
TECHNICAL_ADDENDUM = f"""

---

## INSTRUCCIONES TECNICAS DE SALIDA (uso interno de la app, no mostrar al cliente)

Ademas de redactar el informe completo siguiendo la ESTRUCTURA DE SALIDA de
arriba, debes devolver SOLO un JSON valido (sin texto fuera del JSON) con esta
forma exacta:

{{
  "informe_markdown": "<el informe completo: secciones 1 a 9 tal como pide la ESTRUCTURA DE SALIDA, usando los mismos titulos '### 1. Resumen ejecutivo' etc., MAS una seccion adicional '### 10. Filtro de angulo y avatar (Nova Wave)' explicando el resultado del filtro (ver abajo). Listo para pegar tal cual>",
  "nivel_consciencia": "<una de: {', '.join(AWARENESS_STAGES)}>",
  "segments": [
    {{"start": <segundos>, "end": <segundos>, "awareness_stage": "<una de las 5 etapas>"}}
  ],
  "nicho": "<mejor estimacion del nicho/industria del video, ej. dental, fitness, belleza, finanzas...>",
  "formato": "<estructura viral detectada - usa preferentemente una de las 7 de perfil_cliente/formacion si aplica (Hablar a camara, Doble personaje, Pantalla verde/reaccion, Elecciones y rankings, Entrevista en la calle, Noticia de TV/prensa, Tutorial camuflado); si no encaja en ninguna, usa el framework narrativo clasico (PAS, AIDA, Antes-Despues-Puente, storytelling, listicle...)>",
  "hook": "<resumen del hook en 1 frase corta, para mostrar en listados>",
  "puntuacion": {{
    "hook": <1-10>, "claridad_mensaje": <1-10>, "ejecucion_tecnica": <1-10>,
    "potencial_guardado_compartido": <1-10>, "cta": <1-10>, "alineacion_consciencia": <1-10>,
    "media": <numero, promedio de los 6 ejes>
  }},
  "filtro_angulo_avatar": {{
    "pasa_angulo": <true/false>,
    "pasa_avatar": <true/false>,
    "explicacion": "<2-4 frases: si no hay perfil_cliente declarado, dilo y pon ambos en null; si lo hay, aplica el filtro de dos preguntas del Modulo 1-2 de Nova Wave: 1) esta idea entra dentro del angulo declarado, 2) el avatar declarado consumiria este contenido facilmente>"
  }}
}}

Usa "segments" para dividir el video en 2-6 tramos narrativos con timestamps
(agrupando la transcripcion en bloques con sentido) y asigna a cada uno la
etapa de conciencia de Eugene Schwartz a la que apela en ese momento — esto es
un desglose adicional para la interfaz, coherente con lo que digas en la
seccion 2 del informe pero mas granular.

## FILTRO DE ANGULO Y AVATAR (metodologia interna Nova Wave, Modulo 1-2)

Si se proporciona `perfil_cliente` (angulo, avatar y posicionamiento declarados
por esta cuenta), aplica el filtro de dos preguntas exactamente como lo define
el Modulo 1-2 del curso interno:
1. ¿Esta idea entra dentro del angulo declarado? Si el video se aleja del
   angulo, señalalo claramente — confunde el posicionamiento aunque el video
   sea bueno en si mismo.
2. ¿El avatar declarado consumiria este contenido facilmente? Si el tono, el
   lenguaje o el tema no encajan con ese avatar, señalalo.
Redacta la seccion 10 del informe con el resultado de ambas preguntas y una
recomendacion concreta si alguna falla. Si no hay `perfil_cliente` guardado
para esta cuenta, dilo en una linea en la seccion 10 y no fuerces un
veredicto (deja pasa_angulo/pasa_avatar en null en el JSON).
"""

CLASSIFICATION_SYSTEM_PROMPT = MASTER_PROMPT + TECHNICAL_ADDENDUM


# TikTok (y a veces Instagram) bloquean peticiones anonimas de yt-dlp con
# "Unexpected response from webpage request". Usar cookies de una sesion
# logueada suele arreglarlo. Dos formas, configurables por .env:
#   COOKIES_FILE=ruta/a/cookies.txt   -> mas fiable en Windows (evita el
#     cifrado DPAPI de Chromium), exportado con una extension del navegador.
#   COOKIES_FROM_BROWSER=brave        -> lee directo del navegador (requiere
#     tenerlo completamente cerrado). Si ambas estan definidas, gana COOKIES_FILE.
COOKIES_FILE = os.environ.get("COOKIES_FILE", "").strip()
COOKIES_FROM_BROWSER = os.environ.get("COOKIES_FROM_BROWSER", "").strip()


def _cookie_args():
    if COOKIES_FILE:
        return ["--cookies", COOKIES_FILE]
    if COOKIES_FROM_BROWSER:
        return ["--cookies-from-browser", COOKIES_FROM_BROWSER]
    return []


def get_metadata(url, workdir):
    cmd = ["yt-dlp", "-J", "--no-warnings", *_cookie_args(), url]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=workdir)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-800:])
    return json.loads(result.stdout)


def download_video(url, out_path):
    cmd = ["yt-dlp", "-f", "mp4/best", "-o", out_path, "--no-warnings", *_cookie_args(), url]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def extract_audio(video_path, audio_path):
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "libmp3lame", audio_path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def extract_frames(video_path, out_dir, timestamps=FRAME_TIMESTAMPS):
    frame_paths = []
    for i, t in enumerate(timestamps):
        out_path = os.path.join(out_dir, f"frame_{i}.jpg")
        cmd = ["ffmpeg", "-y", "-ss", str(t), "-i", video_path, "-frames:v", "1", out_path]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        frame_paths.append(out_path)
    return frame_paths


def transcribe_with_segments(client, mp3_path):
    with open(mp3_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="es",
            response_format="verbose_json",
        )
    segments = [
        {"start": s.start, "end": s.end, "text": s.text}
        for s in (result.segments or [])
    ]
    return result.text, segments


def classify_video(
    client, transcript_segments, frame_paths, meta, url,
    notas_manuales=None, autor=None, video_id=None, perfil_cliente=None,
):
    segments_text = "\n".join(
        f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}" for s in transcript_segments
    )

    metadata_text = "\n".join(
        [
            f"plataforma: {detect_platform(url)}",
            f"autor: {autor or '(no disponible)'}",
            f"duracion_segundos: {meta.get('duration')}",
            f"caption: {meta.get('description') or '(no disponible)'}",
            f"audio_usado: {(meta.get('music') or {}).get('title') if isinstance(meta.get('music'), dict) else meta.get('track') or '(no disponible)'}",
        ]
    )
    metricas_text = f"vistas: {meta.get('view_count')}, likes: {meta.get('like_count')} (guardados/compartidos/comentarios no disponibles via yt-dlp)"

    memoria_cliente = get_client_memory(autor, video_id) if autor else None
    memoria_text = (
        memoria_cliente
        or f"(no hay analisis previos guardados para {autor})" if autor else "(no disponible - no se detecto autor)"
    )

    user_text = f"""transcripcion:
{segments_text or '(no disponible)'}

texto_en_pantalla:
(no disponible - no se realiza OCR; si se ve texto en los fotogramas adjuntos, tenlo en cuenta igualmente)

metadata:
{metadata_text}

metricas_reales:
{metricas_text}

notas_manuales:
{notas_manuales or '(vacio)'}

sector_cliente:
(no proporcionado)

perfil_cliente (angulo, avatar y posicionamiento declarados para esta cuenta, Modulo 1-2 Nova Wave):
{perfil_cliente or f"(no hay perfil guardado para {autor or 'esta cuenta'} todavia)"}

historial_cliente (analisis previos de esta misma cuenta, mas recientes primero):
{memoria_text}
Si hay historial, usalo para dar continuidad: senala si se repiten patrones (positivos o
negativos) entre videos de esta cuenta, si aplico alguna recomendacion que ya le diste antes
(y si funciono, segun las metricas), y evita repetir recomendaciones ya dadas salvo que sigan
sin resolverse - en ese caso, dilo explicitamente.

Se adjuntan los fotogramas clave del video (portada/hook y siguientes) como `frames`."""

    content = [{"type": "text", "text": user_text}]
    for frame_path in frame_paths:
        with open(frame_path, "rb") as f:
            frame_b64 = base64.b64encode(f.read()).decode("utf-8")
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}})

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
    )
    return json.loads(response.choices[0].message.content)


def detect_platform(url):
    if "tiktok.com" in url:
        return "tiktok"
    if "instagram.com" in url:
        return "instagram"
    return "otro"


def detect_autor(meta):
    """El @usuario/cuenta que publico el video, segun los metadatos de yt-dlp."""
    autor = meta.get("uploader") or meta.get("channel") or meta.get("uploader_id")
    if autor and not str(autor).startswith("@"):
        autor = f"@{autor}"
    return autor


def extract_section(markdown, header_text):
    """Saca el contenido de una seccion '### N. Titulo' del informe generado."""
    if not markdown:
        return ""
    pattern = rf"###\s*\d+\.\s*{re.escape(header_text)}\s*\n(.*?)(?=\n###\s*\d+\.|\Z)"
    m = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def get_client_memory(autor, exclude_video_id, limit=3):
    """Resumen de los ultimos analisis ya hechos para el mismo @autor (cliente),
    para dar continuidad entre videos en vez de analizar cada uno aislado."""
    if not autor:
        return None

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT hook, puntuacion_media, informe_markdown, created_at
        FROM videos
        WHERE autor = ? AND status = 'done' AND id != ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (autor, exclude_video_id, limit),
    ).fetchall()
    conn.close()

    if not rows:
        return None

    parts = []
    for r in rows:
        resumen = extract_section(r["informe_markdown"], "Resumen ejecutivo")
        recomendaciones = extract_section(r["informe_markdown"], "Recomendaciones concretas")
        parts.append(
            f"- Video del {(r['created_at'] or '')[:10]} (puntuacion {r['puntuacion_media']}/10). "
            f"Hook: {r['hook']}. Resumen: {resumen[:300]}. "
            f"Recomendaciones que ya se le dieron: {recomendaciones[:400]}"
        )
    return "\n".join(parts)


def get_client_profile(autor):
    """Angulo/avatar/posicionamiento declarados para esta cuenta (Modulo 1-2
    Nova Wave), si el usuario los ha rellenado en la app. Devuelve texto listo
    para meter en el prompt, o None si no hay perfil guardado."""
    if not autor:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT angulo, avatar, posicionamiento FROM client_profiles WHERE autor = ?",
        (autor,),
    ).fetchone()
    conn.close()
    if not row or not (row["angulo"] or row["avatar"] or row["posicionamiento"]):
        return None
    return (
        f"Angulo: {row['angulo'] or '(no definido)'}\n"
        f"Avatar: {row['avatar'] or '(no definido)'}\n"
        f"Posicionamiento: {row['posicionamiento'] or '(no definido)'}"
    )


def mark_error(video_id, message):
    conn = get_connection()
    conn.execute(
        "UPDATE videos SET status = 'error', error_message = ?, updated_at = datetime('now') WHERE id = ?",
        (message[:2000], video_id),
    )
    conn.commit()
    conn.close()


def save_result(video_id, url, meta, transcript, classification, frame_files, notas_manuales=None):
    puntuacion = classification.get("puntuacion") or {}
    filtro = classification.get("filtro_angulo_avatar") or {}

    def to_bool_int(v):
        return None if v is None else (1 if v else 0)

    conn = get_connection()
    conn.execute(
        """
        UPDATE videos SET
            status = 'done', platform = ?, autor = ?, duration_seconds = ?, view_count = ?,
            like_count = ?, hook = ?, formato = ?, nicho = ?, awareness_overall = ?,
            transcript = ?, notas_manuales = ?, informe_markdown = ?, puntuacion_media = ?,
            filtro_angulo_pasa = ?, filtro_avatar_pasa = ?, filtro_explicacion = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            detect_platform(url),
            detect_autor(meta),
            meta.get("duration"),
            meta.get("view_count"),
            meta.get("like_count"),
            classification.get("hook"),
            classification.get("formato"),
            classification.get("nicho"),
            classification.get("nivel_consciencia"),
            transcript,
            notas_manuales,
            classification.get("informe_markdown"),
            puntuacion.get("media"),
            to_bool_int(filtro.get("pasa_angulo")),
            to_bool_int(filtro.get("pasa_avatar")),
            filtro.get("explicacion"),
            video_id,
        ),
    )

    # Si es una regeneracion (reanalyze), limpia segmentos/frames anteriores
    # para no acumular duplicados.
    conn.execute("DELETE FROM video_segments WHERE video_id = ?", (video_id,))
    conn.execute("DELETE FROM video_frames WHERE video_id = ?", (video_id,))

    for i, seg in enumerate(classification.get("segments", [])):
        conn.execute(
            """
            INSERT INTO video_segments (video_id, start_seconds, end_seconds, text, awareness_stage, ord)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (video_id, seg.get("start", 0), seg.get("end", 0), seg.get("text", ""), seg.get("awareness_stage"), i),
        )

    for t, path in zip(FRAME_TIMESTAMPS, frame_files):
        with open(path, "rb") as f:
            conn.execute(
                """
                INSERT INTO video_frames (video_id, timestamp_seconds, image_bytes, content_type)
                VALUES (?, ?, ?, 'image/jpeg')
                """,
                (video_id, t, f.read()),
            )

    conn.commit()
    conn.close()


def process_video(video_id, url, notas_manuales=None):
    """Se ejecuta en background (thread) al crear un video, o al regenerar
    su analisis con notas manuales nuevas."""
    client = OpenAI()
    tmp_dir = tempfile.mkdtemp(prefix=f"video_{video_id}_")
    try:
        video_path = os.path.join(tmp_dir, "video.mp4")
        audio_path = os.path.join(tmp_dir, "audio.mp3")

        meta = get_metadata(url, tmp_dir)
        download_video(url, video_path)
        extract_audio(video_path, audio_path)
        frame_files = extract_frames(video_path, tmp_dir)

        transcript, segments = transcribe_with_segments(client, audio_path)
        autor = detect_autor(meta)
        perfil_cliente = get_client_profile(autor)
        classification = classify_video(
            client, segments, frame_files, meta, url, notas_manuales,
            autor=autor, video_id=video_id, perfil_cliente=perfil_cliente,
        )

        save_result(video_id, url, meta, transcript, classification, frame_files, notas_manuales)
    except Exception as e:
        mark_error(video_id, str(e))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def reanalyze_video(video_id, url, notas_manuales=None):
    """Regenera el analisis de un video ya descargado antes. Si el video
    original sigue en cache no hace falta, pero para simplicidad se vuelve a
    descargar (yt-dlp es rapido en la mayoria de los casos)."""
    conn = get_connection()
    conn.execute(
        "UPDATE videos SET status = 'processing', updated_at = datetime('now') WHERE id = ?",
        (video_id,),
    )
    conn.commit()
    conn.close()
    process_video(video_id, url, notas_manuales)
