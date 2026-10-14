"""
Comprueba los capítulos escritos, sin gastar tokens:
  - cotejo:  cada cita «…» y cada bloque > contra la RVR1960 local
  - strong:  cada (H####)/(G####) existe y está en el original de los versículos citados cerca
  - forma:   encabezados, frases prohibidas, números sueltos, enlaces a la serie, NOTA corta
Arregla solo NFC y saltos de línea. Uso:
  python verificar.py archivo.md [más.md] [--libro Isaías] [--plan trabajo/Isaias/plan.json]
"""
import json, re, sys, unicodedata
from pathlib import Path
from comun import db, parse_ref, norm, ORDEN, libro_canonico, RX_REF, sin_tildes

HEB_GR = re.compile(r"[֐-׿Ͱ-Ͽἀ-῿]")
PROHIBIDAS = ["grado de seguridad", "cotejad", "compruebelo", "comprobar antes de repetir",
              "verifique", "segun mis fuentes", "(enlace "]
RX_STRONG = re.compile(r"\(([HG])(\d{1,5})\)")
RX_SUELTO = re.compile(r"(?<![\(\w])([HG]\d{3,5})(?![\w\)])")
RX_ENLACE = re.compile(r"(?P<libro>[1-3]?\s?[A-ZÁÉÍÓÚ][a-záéíóúñ]+(?: de los Cantares)?), tomo (?P<tomo>\d+), "
                       r"(?:capítulo (?P<cap>\d+)|(?P<intro>introducción))\s*\(\*(?P<titulo>[^*]+)\*\)")


# ----------------------------------------------------------------------------
def partes(txt):
    """(cuerpo, nota). La NOTA no se coteja como cuerpo."""
    i = txt.find("## NOTA PARA EL AUTOR")
    return (txt, "") if i < 0 else (txt[:i], txt[i:])


def texto_de(vv):
    q = "select n from rvr where lo=? and cap=? and ver=?"
    return " ".join((db().execute(q, v).fetchone() or [""])[0] for v in vv)


def fragmentos(cita):
    cita = re.sub(r"\*+", "", cita).replace("«", "").replace("»", "")
    return [f for f in re.split(r"…|\.\.\.|\[…\]", cita) if len(norm(f).split()) >= 1]


def en_toda_la_biblia(n):
    return db().execute("select 1 from rvr where n like ? limit 1", (f"%{n}%",)).fetchone() is not None


def comprobar_cita(cita, ref, libro, fallos, sinref, citas_ok):
    frs = [norm(f) for f in fragmentos(cita)]
    frs = [f for f in frs if f]
    if not frs:
        return []
    if ref:
        lib, vv = parse_ref(ref, libro)
        if vv:
            base = texto_de(vv)
            malos = [f for f in frs if f not in base]
            if malos:
                palabras = sorted({w for f in malos for w in f.split() if w not in base.split()})
                fallos.append({"cita": cita[:200], "ref": ref, "no_esta": palabras[:8] or [m[:80] for m in malos[:2]]})
            else:
                citas_ok.append(ref)
            return vv
    # sin referencia: solo se exige si parece una cita larga
    if sum(len(f.split()) for f in frs) >= 5 and not all(en_toda_la_biblia(f) for f in frs):
        sinref.append(cita[:200])
    return []


def cotejo(cuerpo, libro):
    fallos, sinref, ok, versos_citados = [], [], [], []
    lineas = cuerpo.split("\n")
    # 1) bloques de cita
    i = 0
    bloques_txt = set()
    while i < len(lineas):
        if lineas[i].startswith(">"):
            j = i
            while j < len(lineas) and lineas[j].startswith(">"):
                j += 1
            bloque = [l.lstrip(">").strip() for l in lineas[i:j]]
            ref = None
            if bloque and re.match(r"^[—-]\s*", bloque[-1]):
                ref = re.sub(r"^[—-]\s*", "", bloque[-1]); bloque = bloque[:-1]
            texto = " ".join(b for b in bloque if b)
            m = re.search(r"\(([^()]*\d+:\d+[^()]*)\)\s*$", texto)
            if not ref and m:
                ref, texto = m.group(1), texto[:m.start()]
            bloques_txt.add(i)
            for k in range(i, j):
                bloques_txt.add(k)
            if texto.strip():
                versos_citados += comprobar_cita(texto, ref, libro, fallos, sinref, ok)
            i = j
        else:
            i += 1
    # 2) citas «…» dentro del texto
    texto_libre = "\n".join(l for k, l in enumerate(lineas) if k not in bloques_txt and not l.startswith("#"))
    for m in re.finditer(r"«([^«»]{3,}?)»\s*(\((?P<ref>[^()]*?\d+:\d+[^()]*?)\))?", texto_libre):
        ref = m.group("ref")
        if ref:
            # "(Isaías 35:1)" o "(2:3)" o "(2:3; 5:16)"; si trae texto antes, quedarse con la referencia
            r = RX_REF.search(sin_tildes(ref))
            ref = ref[r.start():] if r else ref
        versos_citados += comprobar_cita(m.group(1), ref, libro, fallos, sinref, ok)
    return {"fallos": fallos, "sinref": sinref, "citas_ok": len(ok)}


# ----------------------------------------------------------------------------
def refs_de(parrafo, libro):
    vv = []
    for m in RX_REF.finditer(sin_tildes(parrafo)):
        lib = libro_canonico(m.group("libro"))
        if lib:
            vv += parse_ref(m.group(0), lib)[1]
    for m in re.finditer(r"\((\d+:\d+[\d:,;\-– ]*)\)", parrafo):
        vv += parse_ref(m.group(1), libro)[1]
    return vv


def strongs(cuerpo, libro, texto_capitulo):
    avisos, n = [], 0
    for parrafo in re.split(r"\n\s*\n", cuerpo):
        for m in RX_STRONG.finditer(parrafo):
            n += 1
            num = m.group(1) + m.group(2)
            if not db().execute("select 1 from strong where num=?", (num,)).fetchone() and \
                    db().execute("select count(*) from strong").fetchone()[0]:
                avisos.append(f"{num}: no existe en strong_diccionario")
                continue
            antes = parrafo[max(0, m.start() - 90): m.start()]
            if not HEB_GR.search(antes):
                avisos.append(f"{num}: sin la palabra hebrea/griega delante")
            if "*" not in antes[-80:]:
                avisos.append(f"{num}: falta la transliteración en cursiva")
            vv = refs_de(parrafo, libro) or texto_capitulo
            if vv:
                q = "select 1 from orig where strong=? and (" + " or ".join(["(lo=? and cap=? and ver=?)"] * len(vv[:400])) + ") limit 1"
                args = [num] + [x for v in vv[:400] for x in v]
                if not db().execute(q, args).fetchone():
                    avisos.append(f"{num}: no está en el original de los versículos citados en su párrafo")
    for m in RX_SUELTO.finditer(cuerpo):
        avisos.append(f"{m.group(1)} suelto en la prosa (escribir «el número {m.group(1)[1:]}»)")
    return {"avisos": sorted(set(avisos)), "comprobados": n}


# ----------------------------------------------------------------------------
def titulos_validos(plan):
    s = set()
    for libro, tomo, cap, titulo in db().execute("select libro, tomo, cap, titulo from serie"):
        s.add((norm(libro), int(tomo), str(cap), norm(titulo)))
    if plan:
        for t in plan.get("tomos", []):
            s.add((norm(plan["libro"]), t["tomo"], "intro", norm(t.get("titulo_intro", ""))))
            for c in t["capitulos"]:
                s.add((norm(plan["libro"]), t["tomo"], str(c["cap"]), norm(c["titulo"])))
    return s


def forma(txt, cuerpo, nota, es_intro, validos):
    avisos = []
    lin = txt.split("\n")
    if es_intro:
        if not lin[0].startswith("# Introducción"):
            avisos.append("la primera línea debe ser '# Introducción'")
    else:
        if not re.match(r"# Capítulo \d+$", lin[0]):
            avisos.append("la primera línea debe ser '# Capítulo N'")
        if len(lin) < 2 or not re.match(r"## «.+»$", lin[1]):
            avisos.append("la segunda línea debe ser '## «Título»'")
        for sec in ("### El texto", "## Resumen del capítulo", "## Preguntas de estudio"):
            if sec not in txt:
                avisos.append(f"falta la sección '{sec}'")
        if "Y aquí está la perla del capítulo." not in cuerpo:
            avisos.append("falta la frase 'Y aquí está la perla del capítulo.'")
        # cada apartado ### (salvo El texto) empieza con su versículo citado
        for m in re.finditer(r"^### (?!El texto)(.+)\n+(.*)", cuerpo, re.M):
            if not m.group(2).startswith(">"):
                avisos.append(f"el apartado '{m.group(1)}' no empieza con su versículo citado")
    if not nota:
        avisos.append("falta '## NOTA PARA EL AUTOR'")
    elif len([l for l in nota.split("\n") if l.strip()]) > 14 or len(nota) > 2500:
        avisos.append(f"la NOTA es larga ({len(nota)} caracteres): solo fuentes de fuera, decisiones y correcciones")
    llano = sin_tildes(cuerpo).lower()
    for p in PROHIBIDAS:
        if p in llano:
            avisos.append(f"frase prohibida en el cuerpo: «{p}»")
    if re.search(r"\b20[2-3]\d\b", cuerpo):
        avisos.append("fecha en el cuerpo")
    for m in RX_ENLACE.finditer(cuerpo):
        lib = libro_canonico(m["libro"]) or m["libro"]
        cap = "intro" if m["intro"] else m["cap"]
        clave = (norm(lib), int(m["tomo"]), cap, norm(m["titulo"]))
        if clave not in validos:
            avisos.append(f"enlace que no existe: {m.group(0)}")
    return avisos


# ----------------------------------------------------------------------------
def verificar(ruta, libro=None, plan=None, validos=None):
    ruta = Path(ruta)
    crudo = ruta.read_bytes().decode("utf-8")
    limpio = unicodedata.normalize("NFC", crudo.replace("\r\n", "\n"))
    if limpio != crudo:
        ruta.write_bytes(limpio.encode("utf-8"))
    txt = limpio
    cuerpo, nota = partes(txt)
    es_intro = ruta.name.endswith(("introduccion.md", "-intro.md"))
    # libro: el del plan, o el de la primera referencia de "El texto"
    if not libro:
        m = re.search(r"^>\s*[—-]\s*(.+)$", txt, re.M)
        libro = parse_ref(m.group(1))[0] if m else None
    texto_capitulo = []
    m = re.search(r"### El texto(.*?)(?:\n---|\n### )", txt, re.S)
    if m:
        for r in re.findall(r"^>\s*[—-]\s*(.+)$", m.group(1), re.M):
            texto_capitulo += parse_ref(r, libro)[1]
    validos = validos if validos is not None else titulos_validos(plan)
    inf = {"archivo": ruta.name, "libro": libro,
           "cotejo": cotejo(cuerpo, libro),
           "strong": strongs(cuerpo, libro, texto_capitulo),
           "forma": forma(txt, cuerpo, nota, es_intro, validos),
           "caracteres": len(txt)}
    inf["limpio"] = not (inf["cotejo"]["fallos"] or inf["strong"]["avisos"] or inf["forma"])
    return inf


def resumen(inf):
    c, s = inf["cotejo"], inf["strong"]
    lineas = [f"{inf['archivo']}: {c['citas_ok']} citas bien, {len(c['fallos'])} fallos, "
              f"{len(c['sinref'])} sin referencia; {s['comprobados']} Strong, {len(s['avisos'])} avisos; "
              f"forma {len(inf['forma'])} avisos"]
    for f in c["fallos"]:
        lineas.append(f"  FALLO cita {f['ref']}: «{f['cita'][:120]}» — no está: {f['no_esta']}")
    for f in c["sinref"]:
        lineas.append(f"  SINREF «{f[:120]}» (cítala con referencia o pásala a cursiva sin comillas)")
    for a in s["avisos"]:
        lineas.append(f"  STRONG {a}")
    for a in inf["forma"]:
        lineas.append(f"  FORMA {a}")
    return "\n".join(lineas)


def main():
    args = sys.argv[1:]
    libro = plan = None
    if "--libro" in args:
        i = args.index("--libro"); libro = libro_canonico(args[i + 1]); del args[i:i + 2]
    if "--plan" in args:
        i = args.index("--plan"); plan = json.load(open(args[i + 1], encoding="utf-8")); del args[i:i + 2]
        libro = libro or plan["libro"]
    rutas = []
    for a in args:
        p = Path(a)
        rutas += sorted(p.rglob("*.md")) if p.is_dir() else [p]
    validos = titulos_validos(plan)
    todo_bien = True
    for r in rutas:
        inf = verificar(r, libro, plan, validos)
        print(resumen(inf))
        todo_bien &= inf["limpio"]
    sys.exit(0 if todo_bien else 1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
