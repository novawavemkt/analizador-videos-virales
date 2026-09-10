"""Renderiza el informe de auditoria (HTML standalone) desde el JSON parseado."""

import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_report(data: dict) -> str:
    return _env.get_template("audit_report.html").render(data=data)
