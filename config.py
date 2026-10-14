"""Rutas del proyecto. Funciona en Windows y en la VM del puente (~/mnt/...)."""
import os
from pathlib import Path

AQUI = Path(__file__).resolve().parent            # sophia/herramientas/comentario
SOPHIA = AQUI.parent.parent                         # sophia/


def _primera(*rutas):
    for r in rutas:
        p = Path(os.path.expanduser(r))
        if p.exists():
            return p
    return Path(os.path.expanduser(rutas[0]))


LIBROS = _primera(os.environ.get("LIBROS_LEVIN", r"C:\Users\sinle\OneDrive\Documentos\libros levin"),
                  "~/mnt/libros levin")
DESCARGAS = _primera(os.environ.get("DESCARGAS_BIBLIA", r"C:\Users\sinle\OneDrive\Documentos\descargar biblia"),
                     "~/mnt/descargar biblia")
ASSETS = SOPHIA / "app" / "src" / "main" / "assets" / "original"
TRABAJO = AQUI / "trabajo"
DB = Path(os.environ.get("COMENTARIO_DB", TRABAJO / "biblia.db"))
INDICE = LIBROS / "_indice"

# Modelo y límites de cada llamada a Claude Code
MODELO = os.environ.get("MODELO_COMENTARIO", "opus")
MAX_TURNOS = 60
REINTENTOS_CORRECCION = 2
