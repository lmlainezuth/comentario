# -*- coding: utf-8 -*-
"""
cotejar_citas.py  —  Coteja TODAS las citas biblicas de los libros de Levin
(Genesis, Exodo, Levitico, Numeros, Deuteronomio) contra la RVR1960 guardada
en Supabase (tabla `versiculos`), y saca un informe de las que difieren de verdad.

Metodo (el mismo que validamos a mano en Genesis):
  1. Extrae cada cita (bloque de > ... terminado en  > — Libro cap:vers) de los .md.
  2. Baja de Supabase el texto RVR1960 del/los capitulo(s) citado(s).
  3. Normaliza los dos lados (minusculas, sin acentos ni puntuacion).
  4. Si el fragmento citado NO es subcadena del capitulo, mira que PALABRAS del
     fragmento NO existen en el capitulo:
        - ninguna ausente -> quoteo parcial legitimo (salta versiculos): NO se reporta.
        - alguna ausente  -> posible desvio real de contenido: SE REPORTA, con el
          fragmento del libro y el texto RVR1960 de los versiculos citados al lado.

Uso:
    python cotejar_citas.py                    (la Tora, de Genesis a Deuteronomio)
    python cotejar_citas.py Josue Jueces Rut "1 Samuel" "2 Samuel"
                                               (esos libros; el informe va aparte)
    (ajusta BASE si tus libros estan en otra carpeta)

Ademas de los bloques "> ...", revisa las citas DENTRO del texto («...»): las que
llevan referencia al lado, contra ese capitulo; las que no, contra toda la
RVR1960, por si son una cita de memoria o un dialogo contado con otras palabras
pero entre comillas.

No instala nada (usa urllib). Correr en TU maquina Windows normal, NO en el
sandbox: desde el sandbox Supabase esta bloqueado por la politica de egress.
Las tablas libros/capitulos/versiculos tienen lectura publica, asi que basta
la clave anon de abajo.
"""
import os, re, sys, json, unicodedata, urllib.request, urllib.parse

# ---------- CONFIG ----------
BASE = r"C:\Users\sinle\OneDrive\Documentos\libros levin"
BOOKS = ["Genesis", "Exodo", "Levitico", "Numeros", "Deuteronomio"]
SUPABASE_URL = "https://hvudiurmgrqcirysotdg.supabase.co"
ANON_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh2dWRpdXJtZ3JxY2lyeXNvdGRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE0NDkwNzEsImV4cCI6MjA2NzAyNTA3MX0."
            "DQxa8YbjkhbW0t7uORYa20sK6W4_It8ZWZ77viZJLcU")
VERSION = "RVR1960"
SALIDA = os.path.join(BASE, "informe_cotejo.md")
# ----------------------------

# Con nombres de libro en la linea de ordenes se cotejan esos, y el informe va
# a un archivo aparte, sin pisar el de la Tora:
#     python cotejar_citas.py Josue Jueces Rut "1 Samuel" "2 Samuel"
if len(sys.argv) > 1:
    BOOKS = sys.argv[1:]
    SALIDA = os.path.join(BASE, "informe_cotejo_%s.md"
                          % "_".join(b.replace(" ", "") for b in BOOKS))

DB_NOMBRES = ["Génesis","Éxodo","Levítico","Números","Deuteronomio","Josué","Jueces","Rut",
"1 Samuel","2 Samuel","1 Reyes","2 Reyes","1 Crónicas","2 Crónicas","Esdras","Nehemías","Ester",
"Job","Salmos","Proverbios","Eclesiastés","Cantares","Isaías","Jeremías","Lamentaciones","Ezequiel",
"Daniel","Oseas","Joel","Amós","Abdías","Jonás","Miqueas","Nahúm","Habacuc","Sofonías","Hageo",
"Zacarías","Malaquías","Mateo","Marcos","Lucas","Juan","Hechos","Romanos","1 Corintios","2 Corintios",
"Gálatas","Efesios","Filipenses","Colosenses","1 Tesalonicenses","2 Tesalonicenses","1 Timoteo",
"2 Timoteo","Tito","Filemón","Hebreos","Santiago","1 Pedro","2 Pedro","1 Juan","2 Juan","3 Juan",
"Judas","Apocalipsis"]

def strip_acc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()
def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', strip_acc(s)).strip()

ALIAS = {strip_acc(n): n for n in DB_NOMBRES}
ALIAS["salmo"] = "Salmos"; ALIAS["cantar de los cantares"] = "Cantares"; ALIAS["cantar"] = "Cantares"
ABREV = {"Génesis": "gn gen", "Éxodo": "ex exo", "Levítico": "lv lev", "Números": "nm num",
    "Deuteronomio": "dt deut", "Josué": "jos", "Jueces": "jue jc", "Rut": "rt",
    "1 Samuel": "1 s|1 sm|1 sam", "2 Samuel": "2 s|2 sm|2 sam", "1 Reyes": "1 r|1 re|1 rey",
    "2 Reyes": "2 r|2 re|2 rey", "1 Crónicas": "1 cr|1 cro|1 cron", "2 Crónicas": "2 cr|2 cro|2 cron",
    "Esdras": "esd", "Nehemías": "neh", "Ester": "est", "Salmos": "sal", "Proverbios": "pr prov",
    "Eclesiastés": "ec ecl", "Cantares": "cnt cant", "Isaías": "is isa", "Jeremías": "jer",
    "Lamentaciones": "lm lam", "Ezequiel": "ez ezeq", "Daniel": "dn dan", "Oseas": "os",
    "Joel": "jl", "Amós": "am", "Abdías": "abd", "Jonás": "jon", "Miqueas": "mi miq", "Nahúm": "nah",
    "Habacuc": "hab", "Sofonías": "sof", "Hageo": "hag", "Zacarías": "zac", "Malaquías": "mal",
    "Mateo": "mt mat", "Marcos": "mc mr mar", "Lucas": "lc luc", "Juan": "jn", "Hechos": "hch hech",
    "Romanos": "ro rom", "1 Corintios": "1 co|1 cor", "2 Corintios": "2 co|2 cor", "Gálatas": "ga gal",
    "Efesios": "ef", "Filipenses": "flp fil", "Colosenses": "col", "1 Tesalonicenses": "1 ts|1 tes",
    "2 Tesalonicenses": "2 ts|2 tes", "1 Timoteo": "1 ti|1 tim", "2 Timoteo": "2 ti|2 tim",
    "Tito": "tit", "Filemón": "flm", "Hebreos": "heb", "Santiago": "stg sant", "1 Pedro": "1 p|1 pe|1 ped",
    "2 Pedro": "2 p|2 pe|2 ped", "1 Juan": "1 jn", "2 Juan": "2 jn", "3 Juan": "3 jn", "Judas": "jud",
    "Apocalipsis": "ap apoc"}
for _n, _ab in ABREV.items():
    for _k in re.split(r"\|" if "|" in _ab else r" ", _ab):
        _k = _k.strip()
        if _k and _k not in ALIAS: ALIAS[_k] = _n
ALIAS_KEYS = sorted(ALIAS.keys(), key=len, reverse=True)

# Citas ya revisadas a mano que se quedan como estan (glosas del original,
# erratas de la base, frases hipoteticas...). Una por linea en
# cotejo_aceptadas.txt: "ruta del archivo | texto de la cita". No salen mas.
ACEPTADAS = []
_ok = os.path.join(BASE, "cotejo_aceptadas.txt")
if os.path.exists(_ok):
    for _l in open(_ok, encoding="utf-8"):
        if "|" in _l and not _l.lstrip().startswith("#"):
            _a, _q = _l.split("|", 1)
            ACEPTADAS.append((_a.strip().replace("\\", "/").lower(), norm(_q)))
def aceptada(rel, texto):
    r = rel.replace("\\", "/").lower(); t = norm(texto)
    return any(a == r and q and (q in t or t in q) for a, q in ACEPTADAS)

def api(path):
    req = urllib.request.Request(SUPABASE_URL + path,
        headers={"apikey": ANON_KEY, "Authorization": "Bearer " + ANON_KEY})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

print("Bajando indice de libros y capitulos...")
libros = {l["nombre"]: l["id"] for l in api("/rest/v1/libros?select=id,nombre")}
caps = {}; off = 0
while True:
    part = api("/rest/v1/capitulos?select=id,libro_id,numero&order=id&limit=1000&offset=%d" % off)
    if not part: break
    for c in part: caps[(c["libro_id"], c["numero"])] = c["id"]
    off += len(part)
    if len(part) < 1000: break

def junta(t):
    """La base pega las lineas de la poesia sin espacio ("tus ojosSon"): se separan."""
    return re.sub(r"(?<=[a-záéíóúüñ,;:.!?])(?=[A-ZÁÉÍÓÚÜÑ¿¡])", " ", t)

_vcache = {}  # (libro_id, chap) -> {ver:texto}
def chapter_verses(libro_id, chap):
    k = (libro_id, chap)
    if k in _vcache: return _vcache[k]
    cid = caps.get(k)
    if cid is None: _vcache[k] = None; return None
    vs = api("/rest/v1/versiculos?select=numero,texto&order=numero&capitulo_id=eq.%d&version=eq.%s"
             % (cid, urllib.parse.quote(VERSION)))
    _vcache[k] = {v["numero"]: junta(v["texto"]) for v in vs}
    return _vcache[k]

# La RVR1960 entera de una vez (unas 32 peticiones de 1000 versiculos). Hace
# falta para las citas dentro del texto que no llevan referencia, que pueden
# venir de cualquier libro; y de paso ya no se pide capitulo a capitulo.
print("Bajando la RVR1960 entera...")
_cap_de_id = {cid: k for k, cid in caps.items()}
off = 0
while True:
    part = api("/rest/v1/versiculos?select=capitulo_id,numero,texto&version=eq.%s"
               "&order=capitulo_id,numero&limit=1000&offset=%d"
               % (urllib.parse.quote(VERSION), off))
    if not part: break
    for v in part:
        k = _cap_de_id.get(v["capitulo_id"])
        if k: _vcache.setdefault(k, {})[v["numero"]] = junta(v["texto"])
    off += len(part)

NOMBRE_DE_ID = {i: n for n, i in libros.items()}
# Toda la Biblia normalizada, capitulo tras capitulo; el " | " impide que una
# frase "encaje" saltando de un capitulo al siguiente.
TODA = " | ".join(norm(" ".join(vv[n] for n in sorted(vv)))
                  for _, vv in sorted(_vcache.items()) if vv)
TEXTO_LIBRO = {}
for (_lid, _ch), vv in sorted(_vcache.items()):
    if vv: TEXTO_LIBRO[_lid] = TEXTO_LIBRO.get(_lid, "") + " | " + norm(" ".join(vv[n] for n in sorted(vv)))
def donde_esta(fn):
    for (_l, _c, _v, _t) in VERSOS:
        if fn in norm(_t): return "%s %d:%d" % (NOMBRE_DE_ID.get(_l, "?"), _c, _v)
    return "varios versiculos seguidos"
VERSOS, INDICE = [], {}   # versiculos en orden, y palabra -> versiculos donde sale
for (_lid, _ch), vv in sorted(_vcache.items()):
    for _n in sorted(vv or {}):
        VERSOS.append((_lid, _ch, _n, vv[_n]))
        for w in set(norm(vv[_n]).split()):
            if len(w) >= 4: INDICE.setdefault(w, set()).add(len(VERSOS) - 1)

def parse_ref(refraw):
    """Devuelve (book, chaps set, refspecs) ; refspecs = lista (chap, vlo, vhi)."""
    r = refraw.strip().replace("–", "-").replace("—", "-")   # – y — valen como guion
    rn = strip_acc(r); book = None; rest = ""
    for key in ALIAS_KEYS:
        if rn.startswith(key + " ") or rn == key or rn.startswith(key + ". "):
            book = ALIAS[key]; rest = r[len(key):].lstrip(". ").strip(); break
    if not book: return None, None, None
    chaps = set(); specs = []
    curc = None
    # tokeniza "cap:va-vb, vc" y rangos cruzados "ca:va-cb:vb"
    for part in re.split(r"\s*(?:,|;|\by\b)\s*", rest):
        m = re.match(r"(\d+):(\d+)\s*-\s*(\d+):(\d+)", part)
        if m:
            ca, va, cb, vb = map(int, m.groups())
            chaps.update(range(ca, cb + 1))   # tambien los capitulos de en medio
            specs.append((ca, va, 999));
            for cm in range(ca + 1, cb): specs.append((cm, 1, 999))
            if cb != ca: specs.append((cb, 1, vb))
            curc = cb; continue
        m = re.match(r"(\d+):(\d+)\s*-\s*(\d+)", part)
        if m:
            ca, va, vb = map(int, m.groups()); chaps.add(ca)
            specs.append((ca, va, vb)); curc = ca; continue
        m = re.match(r"(\d+):(\d+)", part)
        if m:
            ca, va = map(int, m.groups()); chaps.add(ca)
            specs.append((ca, va, va)); curc = ca; continue
        m = re.match(r"(\d+)\s*-\s*(\d+)", part)  # "3-4" tras un cap ya visto
        if m and curc:
            va, vb = map(int, m.groups()); specs.append((curc, va, vb)); continue
        if m and not curc:   # "Genesis 2-3": capitulos enteros
            ca, cb = map(int, m.groups()); chaps.update(range(ca, cb + 1)); continue
        m = re.match(r"(\d+)$", part)  # ", 31"
        if m and curc:
            va = int(m.group(1)); specs.append((curc, va, va)); continue
        m = re.match(r"(\d+)$", part)  # "Salmo 132", "Levitico 2 y 3" (solo capitulos)
        if m and not curc:
            chaps.add(int(m.group(1)))
    return book, sorted(chaps), specs

def clean(txt):
    txt = txt.replace("**", "").replace("*", "")
    for ch in "«»“”\"'[]": txt = txt.replace(ch, "")
    txt = txt.replace("…", "§").replace("...", "§")
    return re.sub(r"\s+", " ", txt).strip()

ATTR = re.compile(r"^\s*[—–\-]{1,2}\s*(.+)$")

def verses_text(libro_id, specs):
    out = []
    for (ch, vlo, vhi) in specs:
        vv = chapter_verses(libro_id, ch)
        if not vv: continue
        for num in sorted(vv):
            if vlo <= num <= vhi:
                out.append("%d:%d %s" % (ch, num, vv[num]))
    return out

# ---------- citas dentro del texto: «...» ----------
INLINE = re.compile(r"«([^«»]+)»(?:\s*\(([^()]*)\))?")
REF_EN_LINEA = re.compile(r"\d+:\d+(?:\s*[-–]\s*\d+(?::\d+)?)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*")
# Verbos de decir: si la frase entre comillas va detras de uno (o de dos
# puntos), se pone en boca de alguien, y entonces tiene que ser literal.
DECIR = re.compile(r"\b(dij\w*|dic\w*|respond\w*|pregunt\w*|clam\w*|grit\w*|exclam\w*|"
                   r"confies\w*|confes\w*|susurr\w*|rueg\w*|rog\w*|promet\w*|bendi\w*|"
                   r"declar\w*|orden\w*|mand\w*|anunci\w*|suplic\w*|jur\w*|llor\w*|"
                   r"lament\w*|cant\w*|contest\w*|reconoc\w*|acus\w*|insist\w*|"
                   r"repit\w*|advirt\w*|adviert\w*|anad\w*)\b")

def parecido(fichas, solo_libro=None):
    """
    El versiculo (o el par de versiculos seguidos) que mas palabras comparte
    con la frase. Devuelve (proporcion, [lineas "Libro cap:ver texto"], texto
    normalizado de esos versiculos).
    """
    cuenta = {}
    for w in fichas:
        for i in INDICE.get(w, ()):
            if solo_libro is None or VERSOS[i][0] == solo_libro:
                cuenta[i] = cuenta.get(i, 0) + 1
    if not cuenta: return 0.0, [], ""
    mejor = max(cuenta, key=lambda i: (cuenta[i], -i))
    opciones = [[mejor]]
    for j in (mejor - 1, mejor + 1):
        if 0 <= j < len(VERSOS) and VERSOS[j][:2] == VERSOS[mejor][:2]:
            opciones.append(sorted([mejor, j]))
    top, cual = -1.0, [mejor]
    for op in opciones:
        pal = set()
        for i in op: pal |= set(norm(VERSOS[i][3]).split())
        r = len(fichas & pal) / float(len(fichas))
        if r > top + 1e-9: top, cual = r, op
    return (top, ["%s %d:%d %s" % (NOMBRE_DE_ID.get(VERSOS[i][0], "?"), VERSOS[i][1],
                                   VERSOS[i][2], VERSOS[i][3]) for i in cual],
            " ".join(norm(VERSOS[i][3]) for i in cual))

def racha(a, b):
    """Cuantas palabras seguidas comparten dos textos normalizados, como mucho."""
    a, b = a.split(), b.split(); mejor = 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0] * (len(b) + 1)
        for j, y in enumerate(b, 1):
            if x == y:
                cur[j] = prev[j - 1] + 1
                if cur[j] > mejor: mejor = cur[j]
        prev = cur
    return mejor

# Lo que va entre comillas justo despues de hablar del hebreo, de otra version
# o de lo que "significa" una palabra es una glosa a proposito, no una cita de
# la RVR1960: no se revisa (se cuenta aparte).
MARCAS = re.compile(r"hebre|grieg|literal|traduc|version|\bnvi\b|\blbla\b|\bdhh\b|"
                    r"biblia de|rv ?2004|1909|1569|septuaginta|\blxx\b|significa|"
                    r"quiere decir|original|palabra por palabra|yhvh|masoret|arame")

PRE_REF1 = re.compile(r"\(([^()]*\d+:\d+[^()]*)\)\s*:\s*[*_]*$")
PRE_REF2 = re.compile(r"((?:(?:[1-3]\s)?[A-Za-zÁÉÍÓÚáéíóú]+\.?\s+)?\d+:\d+(?:\s*[-–]\s*\d+(?::\d+)?)?)\s*\(\s*[*_]*$")
def solo_libro(antes):
    """De «Compare Gn» se queda con «Gn»; de «Compare» o «asi en», con nada."""
    pal = antes.split()
    for k in (3, 2, 1):
        if len(pal) >= k:
            cand = " ".join(pal[-k:])
            if parse_ref(cand + " 1:1")[0]: return cand
    return ""
HIPO = re.compile(r"\b(no|nadie|ni|nunca|jamas)\s+(\S+\s+){0,2}$")
def red2(rel, ln, mi, dentro, lid_arch):
    """Segunda red: lo que no salio arriba pero puede ser una cita mal copiada."""
    todo = norm(dentro); ws = todo.split()
    if len(ws) < 2 or aceptada(rel, dentro): return
    if MARCAS.search(strip_acc(ln[max(0, mi.start() - 120):mi.start()])) or re.search(r"\b[HG]\d{2,5}\b", dentro): return
    antes = ln[max(0, mi.start() - 60):mi.start()]
    if HIPO.search(norm(antes[-30:]) + " "): return          # «no dice "..."»: frase hipotetica
    en_boca = ln[:mi.start()].rstrip().endswith(":") or bool(DECIR.search(norm(ln[max(0, mi.start() - 50):mi.start()])))
    ref_cerca = bool(REF_EN_LINEA.search(antes))
    frs = [f for f in (norm(x) for x in clean(dentro).split("§")) if f]
    if all(f in TODA for f in frs):
        if len(ws) > 6 or not lid_arch or not (en_boca or ref_cerca): return
        if all(f in TEXTO_LIBRO.get(lid_arch, "") for f in frs): return
        red2_lista.append((rel, antes.strip(), dentro, "corta y literal, pero no en este libro: %s" % donde_esta(max(frs, key=len)), []))
        return
    fichas = set(w for w in ws if len(w) >= 4)
    r1 = r2 = 0.0; re1 = re2 = []; t1 = t2 = ""
    if fichas and lid_arch: r1, re1, t1 = parecido(fichas, lid_arch)
    if fichas: r2, re2, t2 = parecido(fichas)
    pinta = (r1 >= 0.4 and racha(todo, t1) >= 2) or (r2 >= 0.5 and racha(todo, t2) >= 2)
    if not (en_boca or ref_cerca or pinta): return
    why = "en boca de alguien" if en_boca else ("con referencia cerca" if ref_cerca else "se parece a un versiculo")
    reales = re1 if r1 >= r2 * 0.9 else re2
    red2_lista.append((rel, antes.strip(), dentro, "%s; lo mas parecido (%d%%):" % (why, round(max(r1, r2) * 100)), reales))

reportes = []; reportes_orden = []; red2_lista = []; n_cita = 0; n_frag = 0
reportes_linea = []; n_linea_ref = 0; n_linea_sin = 0; n_glosas = 0; n_aceptadas = 0
for b in BOOKS:
    d = os.path.join(BASE, b)
    if not os.path.isdir(d): print("AVISO: no existe", d); continue
    for root, _, files in os.walk(d):
        for f in sorted(files):
            if not f.endswith(".md"): continue
            p = os.path.join(root, f); rel = os.path.relpath(p, BASE)
            lines = open(p, encoding="utf-8").read().split("\n")
            for i, ln in enumerate(lines):
                s = ln.lstrip()
                if s.startswith(">"): s = s[1:].lstrip()
                m = ATTR.match(s.replace("**", "").strip())
                if not m: continue
                book, chaps, specs = parse_ref(m.group(1))
                if not book or not chaps: continue
                lid = libros.get(book)
                if not lid: continue
                q = []; j = i - 1
                while j >= 0:
                    t = lines[j].lstrip()
                    if t.startswith(">"):
                        c = t[1:].lstrip()
                        if ATTR.match(c.replace("**", "").strip()): break
                        q.append(c); j -= 1
                    else: break
                if not q: continue
                q.reverse(); quote = clean(" ".join(q))
                frags = [fr.strip() for fr in quote.split("§") if len(norm(fr)) >= 12]
                if not frags: continue
                n_cita += 1
                partes = [chapter_verses(lid, ch) for ch in chaps]
                if any(pp is None for pp in partes):
                    reportes.append((rel, m.group(1).strip(), "(ref no encontrada en la base)", "", []))
                    continue
                chtext = norm(" ".join(t for pp in partes if pp for t in pp.values()))
                chwords = set(chtext.split())
                for fr in frags:
                    n_frag += 1
                    fn = norm(fr)
                    if fn and fn not in chtext:
                        ausentes = [w for w in fn.split() if w not in chwords]
                        if ausentes and aceptada(rel, fr): n_aceptadas += 1
                        elif ausentes:
                            reportes.append((rel, m.group(1).strip(), fr,
                                             " ".join(dict.fromkeys(ausentes)),
                                             verses_text(lid, specs)))
                        elif not aceptada(rel, fr):
                            reportes_orden.append((rel, m.group(1).strip(), fr, "", verses_text(lid, specs)))

            # --- Citas dentro del texto: «...» fuera de los bloques > y antes de la nota ---
            libro_arch = ALIAS.get(strip_acc(b))
            lid_arch = libros.get(libro_arch)
            for ln in lines:
                if re.match(r"^\s*#+\s*NOTA PARA EL", ln, re.I): break
                if ln.lstrip().startswith(">"): continue
                for mi in INLINE.finditer(ln):
                    dentro, ref_txt = mi.group(1), (mi.group(2) or "")
                    if not REF_EN_LINEA.search(ref_txt):
                        _pre = ln[max(0, mi.start() - 80):mi.start()]
                        _mp = PRE_REF1.search(_pre) or PRE_REF2.search(_pre)
                        if _mp:
                            ref_txt = _mp.group(1); _mm = REF_EN_LINEA.search(ref_txt)
                            if _mm: ref_txt = (solo_libro(ref_txt[:_mm.start()]) + " " + _mm.group(0)).strip()
                    frags = [fr.strip() for fr in clean(dentro).split("§") if len(norm(fr)) >= 12]
                    if not frags: red2(rel, ln, mi, dentro, lid_arch); continue
                    if aceptada(rel, dentro): n_aceptadas += 1; continue
                    glosa = bool(MARCAS.search(strip_acc(ln[max(0, mi.start() - 120):mi.start()]))
                                 or re.search(r"\b[HG]\d{2,5}\b", dentro))
                    book = chaps = None; implicito = True
                    mr = REF_EN_LINEA.search(ref_txt)
                    if mr:
                        antes = re.sub(r"^(cf\.?|v[eé]ase|ver)\s*", "",
                                       ref_txt[:mr.start()].strip(), flags=re.I).strip(" ,;")
                        antes = solo_libro(antes)
                        implicito = not antes
                        book, chaps, specs = parse_ref((antes or libro_arch or "") + " "
                                                       + mr.group(0))
                    if book and chaps and libros.get(book):
                        lid = libros[book]
                        partes = [chapter_verses(lid, ch) for ch in chaps]
                        if any(pp is None for pp in partes): continue
                        n_linea_ref += 1
                        chtext = norm(" ".join(t for pp in partes if pp for t in pp.values()))
                        chwords = set(chtext.split())
                        for fr in frags:
                            fn = norm(fr)
                            if fn in chtext: continue
                            if glosa: n_glosas += 1; continue
                            # sin libro en el parentesis y literal en otra parte: la frase
                            # nombra otro libro ("como dice Apocalipsis: «...» (21:1)")
                            if implicito and fn in TODA: continue
                            aus = [w for w in fn.split() if w not in chwords]
                            motivo = ("palabras ausentes: _%s_" % " ".join(dict.fromkeys(aus)) if aus
                                      else "las palabras estan en el capitulo, pero no seguidas asi "
                                           "(falta «…» o cambia el orden)")
                            reportes_linea.append((rel, "(%s)" % ref_txt.strip(), fr, motivo,
                                                   verses_text(lid, specs)))
                        continue
                    # Sin referencia: solo se juzga lo que parece cita
                    todo = norm(dentro)
                    if len(todo.split()) < 5: red2(rel, ln, mi, dentro, lid_arch); continue
                    if all(norm(fr) in TODA for fr in frags): red2(rel, ln, mi, dentro, lid_arch); continue
                    fichas = set(w for w in todo.split() if len(w) >= 4)
                    if len(fichas) < 3: red2(rel, ln, mi, dentro, lid_arch); continue
                    if glosa: n_glosas += 1; continue
                    n_linea_sin += 1
                    r_all, reales_all, texto_all = parecido(fichas)
                    # ademas de palabras sueltas, tres seguidas: si no, es una frase propia
                    if r_all >= 0.6 and racha(todo, texto_all) >= 3:
                        reportes_linea.append((rel, "sin referencia", dentro,
                            "no esta tal cual en la RVR1960 y se parece al %d%% a:" % round(r_all * 100),
                            reales_all))
                        continue
                    contexto = norm(ln[max(0, mi.start() - 50):mi.start()])
                    en_boca = ln[:mi.start()].rstrip().endswith(":") or DECIR.search(contexto)
                    if en_boca and lid_arch:
                        r_lib, reales_lib, texto_lib = parecido(fichas, lid_arch)
                        if r_lib >= 0.25 and racha(todo, texto_lib) >= 2:
                            reportes_linea.append((rel, "sin referencia, en boca de alguien", dentro,
                                "no esta tal cual en la RVR1960; lo mas parecido del libro (%d%%):"
                                % round(r_lib * 100), reales_lib))
                            continue
                    red2(rel, ln, mi, dentro, lid_arch)

with open(SALIDA, "w", encoding="utf-8") as out:
    out.write("# Informe de cotejo de citas contra RVR1960\n\n")
    out.write("Citas revisadas: **%d** (fragmentos: %d). Posibles desvios de contenido: **%d**.\n\n"
              % (n_cita, n_frag, len(reportes)))
    out.write("*Solo se listan las citas cuyo fragmento contiene palabras que NO existen en el "
              "capitulo citado (posible error real). Los quoteos que solo saltan versiculos no se "
              "listan: son legitimos.*\n\n")
    out.write("Para cada una: el fragmento **tal como esta en tu libro**, las palabras sospechosas, "
              "y debajo el texto **RVR1960 real** de los versiculos citados. Decide tu.\n\n---\n")
    cur = None
    for rel, ref, frag, ausentes, reales in reportes:
        if rel != cur: out.write("\n## %s\n" % rel); cur = rel
        out.write("\n**%s**  · palabras ausentes: _%s_\n\n" % (ref, ausentes or "(ref no encontrada)"))
        out.write("- Libro: «%s»\n" % frag)
        for rt in reales:
            out.write("- RVR1960 %s\n" % rt)
    if not reportes:
        out.write("\n**Sin desvios de contenido. Todas las citas coinciden con la RVR1960.**\n")
    out.write("\n---\n\n# Bloques > con las palabras del capitulo pero no seguidas\n\n")
    out.write("Fragmentos: **%d**. *Todas sus palabras estan en el capitulo, pero no en ese orden o "
              "no seguidas: falta «…» donde se salta algo, o se cambio el orden o una palabra por "
              "otra del mismo capitulo.*\n" % len(reportes_orden))
    cur = None
    for rel, ref, frag, _x, reales in reportes_orden:
        if rel != cur: out.write("\n## %s\n" % rel); cur = rel
        out.write("\n**%s** · no seguidas\n\n- Libro: «%s»\n" % (ref, frag))
        for rt in reales: out.write("- RVR1960 %s\n" % rt)
    out.write("\n---\n\n# Citas dentro del texto («…»)\n\n")
    out.write("Con referencia al lado: **%d**. Sin referencia (cinco palabras o mas): **%d**. "
              "Posibles desvios: **%d**. Glosas del original u otras versiones, que no se "
              "revisan: **%d**. Aceptadas a mano en cotejo_aceptadas.txt: **%d**.\n\n"
              % (n_linea_ref, n_linea_sin, len(reportes_linea), n_glosas, n_aceptadas))
    out.write("*Con referencia: el fragmento tiene que estar tal cual en el capitulo citado. "
              "Sin referencia: sale si no esta tal cual en ninguna parte de la RVR1960 y, o se "
              "parece mucho a un versiculo (60 % de sus palabras o mas), o va en boca de alguien "
              "(detras de un verbo de decir o de dos puntos) y se parece a algo del libro. Suele "
              "ser una cita de memoria o un dialogo contado con otras palabras pero entre "
              "comillas. Tambien puede ser una frase tuya: decide tu.*\n")
    cur = None
    for rel, ref, frag, motivo, reales in reportes_linea:
        if rel != cur: out.write("\n## %s\n" % rel); cur = rel
        out.write("\n**%s** · %s\n\n" % (ref, motivo))
        out.write("- Libro: «%s»\n" % frag)
        for rt in reales:
            out.write("- RVR1960 %s\n" % rt)
    if not reportes_linea:
        out.write("\n**Sin desvios en las citas dentro del texto.**\n")
    out.write("\n---\n\n# Segunda red: citas «…» que no estan tal cual y no salieron arriba\n\n")
    out.write("Para revisar a mano: **%d**. *Cortas, o poco parecidas a un versiculo, pero puestas en "
              "boca de alguien, junto a una referencia, o con aire de cita; y las cortas que solo "
              "estan tal cual en otro libro. Muchas seran frases tuyas: las buenas se apuntan en "
              "cotejo_aceptadas.txt y no vuelven a salir.*\n" % len(red2_lista))
    cur = None
    for rel, antes, frag, motivo, reales in red2_lista:
        if rel != cur: out.write("\n## %s\n" % rel); cur = rel
        out.write("\n**segunda red** · %s\n\n- Antes: …%s\n- Libro: «%s»\n" % (motivo, antes[-45:], frag))
        for rt in reales: out.write("- RVR1960 %s\n" % rt)

print("\nCitas revisadas:", n_cita, " fragmentos:", n_frag)
print("Posibles desvios:", len(reportes))
print("Citas dentro del texto: %d con referencia, %d sin; posibles desvios: %d; glosas sin revisar: %d; aceptadas: %d"
      % (n_linea_ref, n_linea_sin, len(reportes_linea), n_glosas, n_aceptadas))
print("Bloques > con palabras no seguidas: %d" % len(reportes_orden))
print("Segunda red (para revisar a mano): %d" % len(red2_lista))
print("Informe escrito en:", SALIDA)
