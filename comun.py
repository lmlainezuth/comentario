"""Lo común: libros, normalización, referencias y acceso a la base local."""
import re, sqlite3, unicodedata
from config import DB

LIBROS = [
    "Génesis", "Éxodo", "Levítico", "Números", "Deuteronomio", "Josué", "Jueces", "Rut",
    "1 Samuel", "2 Samuel", "1 Reyes", "2 Reyes", "1 Crónicas", "2 Crónicas", "Esdras",
    "Nehemías", "Ester", "Job", "Salmos", "Proverbios", "Eclesiastés", "Cantares", "Isaías",
    "Jeremías", "Lamentaciones", "Ezequiel", "Daniel", "Oseas", "Joel", "Amós", "Abdías",
    "Jonás", "Miqueas", "Nahúm", "Habacuc", "Sofonías", "Hageo", "Zacarías", "Malaquías",
    "Mateo", "Marcos", "Lucas", "Juan", "Hechos", "Romanos", "1 Corintios", "2 Corintios",
    "Gálatas", "Efesios", "Filipenses", "Colosenses", "1 Tesalonicenses", "2 Tesalonicenses",
    "1 Timoteo", "2 Timoteo", "Tito", "Filemón", "Hebreos", "Santiago", "1 Pedro", "2 Pedro",
    "1 Juan", "2 Juan", "3 Juan", "Judas", "Apocalipsis",
]
ORDEN = {l: i + 1 for i, l in enumerate(LIBROS)}

# Prefijo de archivo por libro (los ya usados + los que faltan)
PREFIJOS = {
    "Isaías": "isa", "Jeremías": "jer", "Lamentaciones": "lam", "Ezequiel": "eze", "Daniel": "dan",
    "Oseas": "os", "Joel": "joel", "Amós": "amos", "Abdías": "abd", "Jonás": "jon", "Miqueas": "miq",
    "Nahúm": "nah", "Habacuc": "hab", "Sofonías": "sof", "Hageo": "hag", "Zacarías": "zac",
    "Malaquías": "mal", "Mateo": "mat", "Marcos": "mar", "Lucas": "luc", "Juan": "juan",
    "Hechos": "hch", "Romanos": "rom", "1 Corintios": "1co", "2 Corintios": "2co", "Gálatas": "gal",
    "Efesios": "efe", "Filipenses": "fil", "Colosenses": "col", "1 Tesalonicenses": "1ts",
    "2 Tesalonicenses": "2ts", "1 Timoteo": "1ti", "2 Timoteo": "2ti", "Tito": "tit",
    "Filemón": "flm", "Hebreos": "heb", "Santiago": "stg", "1 Pedro": "1pe", "2 Pedro": "2pe",
    "1 Juan": "1jn", "2 Juan": "2jn", "3 Juan": "3jn", "Judas": "jud", "Apocalipsis": "apo",
}


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")


def norm(s):
    """Minúsculas, sin tildes ni signos: para comparar citas."""
    s = sin_tildes(s).lower()
    s = re.sub(r"\[[hg]\d+\]", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def carpeta_de(libro):
    """Nombre de la carpeta en 'libros levin' (sin tildes)."""
    return sin_tildes(libro)


# --- nombres de libro en el texto --------------------------------------------
_ALIAS = {sin_tildes(l).lower(): l for l in LIBROS}
_ALIAS.update({"salmo": "Salmos", "cantar de los cantares": "Cantares", "cantar": "Cantares",
               "eclesiastes": "Eclesiastés", "apocalipsis": "Apocalipsis"})
_ABREV = {"gn": "Génesis", "gen": "Génesis", "ex": "Éxodo", "lv": "Levítico", "nm": "Números",
          "dt": "Deuteronomio", "jos": "Josué", "jue": "Jueces", "rt": "Rut", "1 s": "1 Samuel",
          "2 s": "2 Samuel", "1 r": "1 Reyes", "2 r": "2 Reyes", "1 cr": "1 Crónicas",
          "2 cr": "2 Crónicas", "esd": "Esdras", "neh": "Nehemías", "est": "Ester", "sal": "Salmos",
          "pr": "Proverbios", "ec": "Eclesiastés", "cnt": "Cantares", "is": "Isaías", "jer": "Jeremías",
          "lm": "Lamentaciones", "ez": "Ezequiel", "dn": "Daniel", "os": "Oseas", "jl": "Joel",
          "am": "Amós", "abd": "Abdías", "jon": "Jonás", "mi": "Miqueas", "nah": "Nahúm",
          "hab": "Habacuc", "sof": "Sofonías", "hag": "Hageo", "zac": "Zacarías", "mal": "Malaquías",
          "mt": "Mateo", "mr": "Marcos", "lc": "Lucas", "jn": "Juan", "hch": "Hechos", "ro": "Romanos",
          "1 co": "1 Corintios", "2 co": "2 Corintios", "ga": "Gálatas", "ef": "Efesios",
          "fil": "Filipenses", "col": "Colosenses", "he": "Hebreos", "stg": "Santiago",
          "1 p": "1 Pedro", "2 p": "2 Pedro", "1 jn": "1 Juan", "ap": "Apocalipsis"}
_NOMBRES = sorted(set(_ALIAS) | set(_ABREV), key=len, reverse=True)
_RX_LIBRO = "|".join(re.escape(n) for n in _NOMBRES)
# "Isaías 1:18-20; 2:3, 5" -> libro + cola de números
RX_REF = re.compile(r"(?<![\wÁÉÍÓÚáéíóúñÑ])(?P<libro>" + _RX_LIBRO + r")\.?\s+(?P<cola>\d+:\d+(?:[\d:,;\-–\s]|y\s)*)",
                    re.IGNORECASE)
RX_COLA = re.compile(r"\d+:\d+(?:[\d:,;\-–\s]|y\s)*")


def libro_canonico(nombre):
    k = sin_tildes(nombre).lower().strip().rstrip(".")
    return _ALIAS.get(k) or _ABREV.get(k)


# --- base local --------------------------------------------------------------
_con = None


def db():
    global _con
    if _con is None:
        if not DB.exists():
            raise SystemExit(f"No existe {DB}. Ejecuta primero: python preparar.py")
        _con = sqlite3.connect(str(DB))
    return _con


def max_vers(lo, cap):
    r = db().execute("select max(ver) from rvr where lo=? and cap=?", (lo, cap)).fetchone()
    return r[0] or 0


def expandir(cola, libro):
    """'1:18-20; 2:3, 5' o '4:8-5:1' -> [(lo, cap, ver), ...]"""
    lo = ORDEN[libro]
    out, cap = [], None
    cola = cola.replace("–", "-").replace(" y ", ", ")
    for bloque in re.split(r";", cola):
        for trozo in bloque.split(","):
            trozo = trozo.strip()
            if not trozo:
                continue
            m = re.fullmatch(r"(?:(\d+):)?(\d+)(?:-(?:(\d+):)?(\d+))?", trozo)
            if not m:
                continue
            c1, v1, c2, v2 = m.groups()
            if c1:
                cap = int(c1)
            if cap is None:
                continue
            v1 = int(v1)
            if v2 is None:
                out.append((lo, cap, v1))
            elif c2:  # cruza capítulo: 4:8-5:1
                c2, v2 = int(c2), int(v2)
                for c in range(cap, c2 + 1):
                    a = v1 if c == cap else 1
                    b = v2 if c == c2 else max_vers(lo, c)
                    out += [(lo, c, v) for v in range(a, b + 1)]
                cap = c2
            else:
                out += [(lo, cap, v) for v in range(v1, int(v2) + 1)]
    return out


def parse_ref(texto, libro_defecto=None):
    """Referencia completa ('Isaías 1:18') o corta ('1:18') con libro por defecto."""
    texto = sin_tildes(unicodedata.normalize("NFC", texto.strip()))
    m = RX_REF.search(texto)
    if m and m.start() < 3:
        libro = libro_canonico(m.group("libro"))
        return libro, expandir(m.group("cola"), libro)
    m = RX_COLA.search(texto)
    if m and libro_defecto:
        return libro_defecto, expandir(m.group(0), libro_defecto)
    return None, []


def texto_rvr(vv, tabla="rvr"):
    q = f"select texto from {tabla} where lo=? and cap=? and ver=?"
    return [(v, (db().execute(q, v).fetchone() or [""])[0]) for v in vv]


def fmt_ref(libro, cap, ver=None):
    return f"{libro} {cap}:{ver}" if ver else f"{libro} {cap}"
