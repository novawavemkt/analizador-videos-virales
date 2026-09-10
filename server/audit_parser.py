"""
Parseo de las pestañas de la plantilla de auditoria de Novawave al JSON
intermedio que consume la plantilla del informe (server/templates/audit_report.html).

REGLAS (del brief, no negociables):
  - Cero inferencia. Solo se transforma lo que el humano ya escribio en el sheet.
  - Celda vacia -> el campo se omite (no se rellena con suposicion).
  - Pestaña entera ausente -> su clave no se crea -> la seccion desaparece.
  - El estado (pos/warn/neg) se deriva del emoji/texto de la celda, nunca del color.

NOTA DE MANTENIMIENTO: la plantilla real de Google Sheets tiene 28 pestañas y
cada sub-bloque de 1-Auditoria / 2-Competidores tiene su propia forma de tabla.
Este parser esta escrito contra la descripcion del brief y la forma de datos del
mockup; los nombres de cabecera y el offset de columnas hay que ajustarlos
contra un sheet real la primera vez (ver checklist de verificacion del plan).
"""

import re

from audit_sheets import norm

# ---------------------------------------------------------------------------
# Estado (emoji / texto -> pos | warn | neg | neu)
# ---------------------------------------------------------------------------

# Emojis primero (senal mas fuerte), luego palabras. Solo palabras NORMALIZADAS
# (mayusculas, sin tildes) y NO vacias -> nunca meter "" en las listas.
_POS_EMOJI = ("✅", "🟢", "✔")
_WARN_EMOJI = ("⚠️", "⚠", "🟡", "🟠")
_NEG_EMOJI = ("❌", "🔴", "✖")
_POS_WORDS = ("ACTIVA", "SI ", "BIEN", "VERDE", "CORRECTO", "OK", "RESUELTO")
_WARN_WORDS = ("PARCIAL", "MEJORABLE", "A MEDIAS", "REVISAR", "AMBAR", "NARANJA")
_NEG_WORDS = ("SIN PERFIL", "AUSENTE", "SIN RESULTADOS", "NO EXISTE", "FALTA", "ROJO")


def estado(cell):
    raw = str(cell or "")
    t = f" {norm(cell)} "  # espacios a los lados para poder buscar 'SI ' como palabra
    if any(e in raw for e in _POS_EMOJI) or any(w in t for w in _POS_WORDS):
        return "pos"
    if any(e in raw for e in _WARN_EMOJI) or any(w in t for w in _WARN_WORDS):
        return "warn"
    if any(e in raw for e in _NEG_EMOJI) or any(w in t for w in _NEG_WORDS):
        return "neg"
    return "neu"


def _clean(v):
    return str(v).strip() if v is not None else ""


def _row_has_content(row):
    return any(_clean(c) for c in (row or []))


# ---------------------------------------------------------------------------
# Patron A: lista de pares etiqueta -> valor (col A = etiqueta, col B = valor)
# ---------------------------------------------------------------------------

def parse_label_value(rows):
    out = {}
    for row in rows or []:
        if not _row_has_content(row):
            continue
        label = _clean(row[0]) if len(row) > 0 else ""
        value = _clean(row[1]) if len(row) > 1 else ""
        if not label or not value:
            continue
        out[label] = value
    return out


# ---------------------------------------------------------------------------
# Patron B: tabla ancha partida en sub-bloques por cabecera
# ---------------------------------------------------------------------------

def _header_match(row, keys_norm):
    """Una fila es cabecera de sub-bloque solo si tiene 1 unica celda con
    contenido y esa celda (quitando bullets/simbolos del principio) empieza por
    una de las claves. Asi 'Definir keywords unicas...' (un paso del resumen) NO
    se confunde con la cabecera 'KEYWORDS'."""
    cells = [c for c in (row or []) if _clean(c)]
    if len(cells) != 1:
        return None
    first = norm(re.sub(r"^[^\w]+", "", _clean(cells[0])))
    return next((k for k in keys_norm if k and first.startswith(k)), None)


def split_blocks(rows, header_keys):
    """Devuelve {clave_normalizada_de_cabecera: [filas del bloque]}."""
    blocks = {}
    current = None
    keys_norm = [norm(k) for k in header_keys]
    for row in rows or []:
        matched = _header_match(row, keys_norm)
        if matched:
            current = matched
            blocks.setdefault(current, [])
            continue
        if current is not None and _row_has_content(row):
            blocks[current].append(row)
    return blocks


# ---------------------------------------------------------------------------
# 1-AUDITORIA  (6 sub-bloques)
# ---------------------------------------------------------------------------

AUDIT_HEADERS = {
    "redes": "REDES SOCIALES",
    "keywords": "KEYWORDS",
    "tono": "TONO Y VOZ",
    "identidad": "IDENTIDAD VISUAL",
    "visibilidad": "VISIBILIDAD",
    "opiniones": "OPINIONES",
    "resumen": "RESUMEN",
}


def parse_auditoria(rows):
    blocks = split_blocks(rows, list(AUDIT_HEADERS.values()))
    out = {}

    def b(key):
        return blocks.get(norm(AUDIT_HEADERS[key]), [])

    # -- redes sociales: Canal | Perfil/URL | Propietario | Acceso | Estado | Observaciones
    redes = []
    for r in b("redes"):
        canal = _clean(r[0]) if len(r) > 0 else ""
        if not canal or norm(canal) in ("CANAL", "RED SOCIAL", "RED"):
            continue
        redes.append({
            "red": canal,
            "url": _clean(r[1]) if len(r) > 1 else "",
            "propietario": _clean(r[2]) if len(r) > 2 else "",
            "acceso": _clean(r[3]) if len(r) > 3 else "",
            "estado": estado(r[4] if len(r) > 4 else ""),
            "estado_texto": _clean(r[4]) if len(r) > 4 else "",
            "observaciones": _clean(r[5]) if len(r) > 5 else "",
        })
    if redes:
        out["redes_sociales"] = redes

    # -- keywords: Real | Aspiracional | En contenido | En web | Observaciones
    kws = []
    for r in b("keywords"):
        real = _clean(r[0]) if len(r) > 0 else ""
        if not real or norm(real) in ("REAL", "USAS", "KEYWORD REAL"):
            continue
        kws.append({
            "real": real,
            "aspiracional": _clean(r[1]) if len(r) > 1 else "",
            "en_contenido": _clean(r[2]) if len(r) > 2 else "",
            "en_web": _clean(r[3]) if len(r) > 3 else "",
            "estado": estado(r[2] if len(r) > 2 else ""),
            "observaciones": _clean(r[4]) if len(r) > 4 else "",
        })
    if kws:
        out["keywords"] = kws

    # -- tono y voz: pares etiqueta->valor
    tono = parse_label_value(b("tono"))
    if tono:
        out["tono_voz"] = {
            "tono": tono.get("Tono") or tono.get("TONO") or "",
            "voz": tono.get("Voz") or tono.get("VOZ") or "",
            "adaptacion_por_red": tono.get("Adaptación por red") or tono.get("Adaptacion por red") or "",
            "recomendacion": tono.get("Recomendación") or tono.get("Recomendacion") or "",
        }

    # -- identidad visual: pares pregunta->respuesta (con emoji de estado incrustado)
    ident_rows = b("identidad")
    ident = []
    for r in ident_rows:
        q = _clean(r[0]) if len(r) > 0 else ""
        a = _clean(r[1]) if len(r) > 1 else ""
        if not q or not a:
            continue
        ident.append({"pregunta": q, "respuesta": a, "estado": estado(a)})
    if ident:
        out["identidad_visual"] = ident

    # -- visibilidad en google: Seccion | Marca | KW generica | KW larga | KW+ciudad
    vis = []
    for r in b("visibilidad"):
        sec = _clean(r[0]) if len(r) > 0 else ""
        if not sec or norm(sec) in ("SECCION", "SECCIÓN", ""):
            continue
        vis.append({
            "seccion": sec,
            "marca": _clean(r[1]) if len(r) > 1 else "",
            "kw_generica": _clean(r[2]) if len(r) > 2 else "",
            "kw_larga": _clean(r[3]) if len(r) > 3 else "",
            "kw_ciudad": _clean(r[4]) if len(r) > 4 else "",
        })
    if vis:
        out["visibilidad_google"] = vis

    # -- opiniones: Tipo | Comentario | Plataforma | Fecha | Aspecto clave | Accion
    ops = []
    for r in b("opiniones"):
        comentario = _clean(r[1]) if len(r) > 1 else _clean(r[0]) if len(r) > 0 else ""
        if not comentario or norm(comentario) in ("COMENTARIO", "OPINION", "OPINIÓN"):
            continue
        ops.append({
            "tipo": estado(r[0] if len(r) > 0 else "") if len(r) > 0 else "neu",
            "comentario": comentario,
            "plataforma": _clean(r[2]) if len(r) > 2 else "",
            "fecha": _clean(r[3]) if len(r) > 3 else "",
            "aspecto_clave": _clean(r[4]) if len(r) > 4 else "",
            "accion": _clean(r[5]) if len(r) > 5 else "",
        })
    if ops:
        out["opiniones"] = ops

    # -- resumen: veredictos (Area | Estado | Texto) + proximos pasos
    res_rows = b("resumen")
    veredictos, pasos = [], []
    for r in res_rows:
        c0 = _clean(r[0]) if len(r) > 0 else ""
        c1 = _clean(r[1]) if len(r) > 1 else ""
        c2 = _clean(r[2]) if len(r) > 2 else ""
        if c0 and c2:
            veredictos.append({"area": c0, "estado": estado(c1 or c0), "texto": c2})
        elif c0 and not c1 and not c2:
            pasos.append(c0)
    resumen = {}
    if veredictos:
        resumen["veredictos"] = veredictos
    if pasos:
        resumen["proximos_pasos"] = pasos
    if resumen:
        out["resumen"] = resumen

    return out


# ---------------------------------------------------------------------------
# 2-COMPETIDORES
# ---------------------------------------------------------------------------

def parse_competidores(rows):
    blocks = split_blocks(rows, ["ASPECTO GENERAL", "RED SOCIAL", "CONCLUSION", "CONCLUSIÓN"])
    out = {}

    gen = blocks.get(norm("ASPECTO GENERAL"), [])
    aspecto_general = []
    for r in gen:
        asp = _clean(r[0]) if len(r) > 0 else ""
        if not asp or norm(asp) in ("ASPECTO", "METRICA", "MÉTRICA"):
            continue
        aspecto_general.append({
            "aspecto": asp,
            "tu_marca": _clean(r[1]) if len(r) > 1 else "",
            "competidor_real": _clean(r[2]) if len(r) > 2 else "",
            "aspiracional": _clean(r[3]) if len(r) > 3 else "",
        })
    if aspecto_general:
        out["aspecto_general"] = aspecto_general

    red = blocks.get(norm("RED SOCIAL"), [])
    metricas = []
    for r in red:
        met = _clean(r[0]) if len(r) > 0 else ""
        if not met or norm(met) in ("METRICA", "MÉTRICA"):
            continue
        metricas.append({
            "metrica": met,
            "tu_marca": _clean(r[1]) if len(r) > 1 else "",
            "competidor_real": _clean(r[2]) if len(r) > 2 else "",
            "aspiracional": _clean(r[3]) if len(r) > 3 else "",
        })
    if metricas:
        out["por_red"] = [{"red": "Instagram", "metricas": metricas}]

    concl = blocks.get(norm("CONCLUSION"), []) or blocks.get(norm("CONCLUSIÓN"), [])
    texto = " ".join(_clean(c) for r in concl for c in r if _clean(c)).strip()
    if texto:
        out["conclusion"] = texto

    return out or None


# ---------------------------------------------------------------------------
# 3-SECTOR
# ---------------------------------------------------------------------------

def parse_sector(rows):
    blocks = split_blocks(rows, ["INSIGHT", "OPORTUNIDAD", "FUENTE", "FUENTES"])
    insights, fuentes = [], []

    ins_rows = blocks.get(norm("INSIGHT"), []) or rows or []
    for r in ins_rows:
        ins = _clean(r[0]) if len(r) > 0 else ""
        opp = _clean(r[1]) if len(r) > 1 else ""
        if not ins or norm(ins) in ("INSIGHT", "PROBLEMA"):
            continue
        item = {"insight": ins}
        if opp:
            item["oportunidad"] = opp
        insights.append(item)

    fu_rows = blocks.get(norm("FUENTE"), []) or blocks.get(norm("FUENTES"), [])
    for r in fu_rows:
        fuente = _clean(r[0]) if len(r) > 0 else ""
        dato = _clean(r[1]) if len(r) > 1 else ""
        if not fuente:
            continue
        item = {"fuente": fuente}
        if dato:
            item["dato"] = dato
        fuentes.append(item)

    out = {}
    if insights:
        out["sector_insights"] = insights
    if fuentes:
        out["sector_fuentes"] = fuentes
    return out


# ---------------------------------------------------------------------------
# 4-PUBLICO OBJETIVO  (buyer personas)
# ---------------------------------------------------------------------------

_PERSONA_FIELDS = {
    "nombre": ("NOMBRE",),
    "demografia": ("DEMOGRAFIA", "DEMOGRÁFICA", "PERFIL"),
    "identificadores": ("IDENTIFICADOR",),
    "objetivos": ("OBJETIVO",),
    "retos": ("RETO", "DESAFIO", "DESAFÍO"),
    "aporte": ("APORTA", "QUE LE APORTA", "APORTE"),
    "mensaje_marketing": ("MENSAJE DE MARKETING", "MARKETING"),
    "mensaje_ventas": ("MENSAJE DE VENTAS", "VENTAS"),
}


def parse_publico(rows):
    """La pestaña puede traer 1-2 personas en columnas (B, C) o apiladas.
    Se soporta el formato en columnas: col A = etiqueta, col B = persona 1, col C = persona 2."""
    kv = {}
    ncols = 0
    for r in rows or []:
        if not _row_has_content(r):
            continue
        label = _clean(r[0]) if len(r) > 0 else ""
        vals = [_clean(c) for c in r[1:]] if len(r) > 1 else []
        if label:
            kv[norm(label)] = vals
            ncols = max(ncols, len(vals))

    personas = []
    for i in range(ncols):
        p = {}
        for field, keys in _PERSONA_FIELDS.items():
            for k in kv:
                if any(nk in k for nk in (norm(x) for x in keys)):
                    v = kv[k][i] if i < len(kv[k]) else ""
                    if v:
                        p[field] = v
                    break
        if p.get("nombre") or len(p) >= 2:
            personas.append(p)
    return personas or None


# ---------------------------------------------------------------------------
# TARGET-1 .. TARGET-9  y  CONCLUSION TARGET
# ---------------------------------------------------------------------------

_TARGET_SLOTS = {
    1: "demografia", 2: "socioeconomica", 3: "influencers", 4: "intereses",
    5: "afinidad_mediatica", 6: "contenido", 7: "personalidad",
    8: "mentalidad_compra", 9: "habitos",
}


def parse_conclusion_target(rows):
    kv = parse_label_value(rows)
    if not kv:
        return None
    def pick(*keys):
        for k in kv:
            if any(norm(x) in norm(k) for x in keys):
                return kv[k]
        return ""
    out = {}
    for field, keys in [
        ("perfil_general", ("PERFIL GENERAL", "PERFIL")),
        ("necesidades", ("NECESIDAD", "DESAFIO", "DESAFÍO")),
        ("motivaciones", ("MOTIVACION", "MOTIVACIÓN")),
        ("segmento_adicional", ("SEGMENTO ADICIONAL", "SEGMENTO")),
        ("implicaciones", ("IMPLICACION", "IMPLICACIÓN", "ESTRATEGIA")),
    ]:
        v = pick(*keys)
        if v:
            out[field] = v
    return out or None


# ---------------------------------------------------------------------------
# ENSAMBLADO
# ---------------------------------------------------------------------------

def parse_workbook(sheets):
    """sheets = {nombre_pestaña: [[celda,...],...]}  (ya sin las de EJEMPLO)."""
    data = {}
    target = {}

    for title, rows in sheets.items():
        n = norm(title)

        if "AUDITORIA" in n:
            data.update(parse_auditoria(rows))
            # nombre del cliente: a veces esta en la primera fila de esta pestaña
            for r in rows[:5]:
                for c in (r or []):
                    cn = norm(c)
                    if cn.startswith("CLIENTE") or cn.startswith("MARCA"):
                        parts = _clean(c).split(":", 1)
                        if len(parts) == 2 and parts[1].strip():
                            data.setdefault("cliente", parts[1].strip())
        elif "COMPETIDOR" in n:
            comp = parse_competidores(rows)
            if comp:
                data["competidores"] = comp
        elif "SECTOR" in n:
            data.update(parse_sector(rows))
        elif "PUBLICO OBJETIVO" in n or "PUBLICO" in n:
            bp = parse_publico(rows)
            if bp:
                data["buyer_personas"] = bp
        elif "CONCLUSION TARGET" in n or "CONCLUSION DE TARGET" in n or "CONCLUSION AUDIENCIA" in n:
            ct = parse_conclusion_target(rows)
            if ct:
                data["conclusion_target"] = ct
        elif "TARGET" in n:
            m = None
            for num, slot in _TARGET_SLOTS.items():
                if f"TARGET-{num}" in n or f"TARGET {num}" in n:
                    m = slot
                    break
            if m:
                kv = parse_label_value(rows)
                if kv:
                    target[m] = kv

    if target:
        data["target"] = target
    return data
