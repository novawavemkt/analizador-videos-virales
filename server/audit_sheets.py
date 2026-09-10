"""
Lectura de Google Sheets para la feature de informes de auditoria.

Usa una cuenta de servicio (los sheets viven en el Drive de equipo de Novawave
y se comparten con el email de esa cuenta). Configurable via:
    GOOGLE_SERVICE_ACCOUNT_FILE  (ruta al JSON de la cuenta de servicio)

Devuelve las celdas como texto plano (FORMATTED_VALUE), que incluye los emojis
de estado (checkmark / warning / cross) que la plantilla usa como fuente de
verdad.
"""

import os
import re
import unicodedata

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")


def extract_spreadsheet_id(url_or_id):
    """Acepta un link completo de Google Sheets o directamente el ID."""
    if not url_or_id:
        raise ValueError("Falta el link del Google Sheet.")
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url_or_id)
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", url_or_id.strip()):
        return url_or_id.strip()
    raise ValueError("El link no parece un Google Sheet valido.")


def norm(s):
    """Mayusculas, sin tildes, sin espacios sobrantes. Para comparar nombres
    de pestaña / cabeceras de forma tolerante."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def _build_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            f"No se encuentra el JSON de la cuenta de servicio ('{SERVICE_ACCOUNT_FILE}'). "
            "Ver README (Feature 2) para crearla y compartir la carpeta de Drive."
        )
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def read_sheet(url_or_id):
    """Devuelve {nombre_pestaña: [[celda, ...], ...]} solo de las pestañas de
    trabajo (descarta cualquiera cuyo nombre contenga 'EJEMPLO')."""
    spreadsheet_id = extract_spreadsheet_id(url_or_id)
    service = _build_service()

    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    all_titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
    work_titles = [t for t in all_titles if "EJEMPLO" not in norm(t)]
    if not work_titles:
        raise ValueError("El sheet no tiene ninguna pestaña de trabajo (todas contienen 'EJEMPLO').")

    resp = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id,
        ranges=work_titles,
        valueRenderOption="FORMATTED_VALUE",
    ).execute()

    out = {}
    for rng in resp.get("valueRanges", []):
        # rango vuelve como "'Nombre Pestaña'!A1:Z999" -> recuperar el titulo
        raw = rng.get("range", "")
        title = raw.split("!")[0].strip().strip("'").replace("''", "'")
        out[title] = rng.get("values", [])
    return out
