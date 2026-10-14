"""Lee los libros ya escritos ('libros levin') y reconstruye el índice (_indice)."""
import json, re, sys, unicodedata
from pathlib import Path
from config import LIBROS as RAIZ, INDICE
from comun import LIBROS, sin_tildes, parse_ref

POR_CARPETA = {sin_tildes(l): l for l in LIBROS}
RX_ARCH = re.compile(r"^(?P<pre>.+?)-(?P<tomo>\d{2})-(?P<slug>.+)-(?P<parte>cap(?P<cap>\d{2})|introduccion|intro)\.md$")


def archivos():
    """[(libro, tomo, cap|'intro', ruta)] de todos los .md de la serie."""
    out = []
    for carpeta in sorted(RAIZ.iterdir()):
        if not carpeta.is_dir() or carpeta.name.startswith(("_", ".")):
            continue
        libro = POR_CARPETA.get(carpeta.name)
        if not libro:
            continue
        for md in sorted(carpeta.glob("capitulo */*.md")):
            m = RX_ARCH.match(md.name)
            if not m:
                continue
            cap = int(m["cap"]) if m["cap"] else "intro"
            out.append((libro, int(m["tomo"]), cap, md))
    return out


def ficha(libro, tomo, cap, md):
    txt = md.read_text(encoding="utf-8")
    titulo = ""
    for linea in txt.splitlines():
        if linea.startswith("## "):
            titulo = linea[3:].strip().strip("«»").strip()
            break
    # pasaje principal: primera referencia '> — Libro c:v' bajo '### El texto'
    pasaje = []
    m = re.search(r"### El texto(.*?)(?:\n---|\n### )", txt, re.S)
    if m:
        for r in re.findall(r"^>\s*[—-]\s*(.+)$", m.group(1), re.M):
            lib, vv = parse_ref(r)
            if lib == libro:
                pasaje += vv
    return {"libro": libro, "tomo": tomo, "cap": cap, "titulo": titulo, "archivo": md.name,
            "ruta": str(md), "pasaje": pasaje, "texto": txt}


def todas():
    return [ficha(*a) for a in archivos()]


def rango(pasaje):
    if not pasaje:
        return ""
    a, b = pasaje[0], pasaje[-1]
    return f"{a[1]}:{a[2]} – {b[1]}:{b[2]}"


def previos():
    """Líneas del índice actual por archivo: las que ya existen no se tocan."""
    lin, js = {}, {}
    t, j = INDICE / "titulos.txt", INDICE / "indice_titulos.json"
    if t.exists():
        for l in t.read_text(encoding="utf-8").splitlines():
            p = l.split("|")
            if len(p) == 5:
                lin[p[4]] = l
    if j.exists():
        for e in json.loads(j.read_text(encoding="utf-8")):
            js[e[-1]] = e
    return lin, js


def reconstruir_indice(fichas=None, rangos=None):
    """_indice/todo.md, titulos.txt e indice_titulos.json. Respeta las líneas que ya había y
    añade las de los archivos nuevos. rangos: {archivo_introduccion: 'Isaías 1:1 – 5:30'}."""
    fichas = fichas or todas()
    rangos = rangos or {}
    viejas, viejos_js = previos()
    INDICE.mkdir(exist_ok=True)
    rel = lambda f: "./" + Path(f["ruta"]).relative_to(RAIZ).as_posix()
    with open(INDICE / "todo.md", "w", encoding="utf-8", newline="\n") as fh:
        for f in fichas:
            fh.write(f"###FILE### {rel(f)}\n{f['texto']}\n")
    js, lineas = [], []
    for f in fichas:
        a = f["archivo"]
        if a in viejas and a in viejos_js:
            lineas.append(viejas[a]); js.append(viejos_js[a]); continue
        carpeta = sin_tildes(f["libro"])
        if f["cap"] == "intro":
            vol = {}
            vt = Path(f["ruta"]).parent.parent / "volumenes.txt"
            if vt.exists():
                for l in vt.read_text(encoding="utf-8").splitlines():
                    k, _, v = l.partition("=")
                    if v and k.strip().isdigit():
                        vol[int(k)] = v.strip()
            rg = rangos.get(a) or f"{f['libro']} {rango_tomo(fichas, f)}"
            lineas.append(f"{carpeta}|{f['tomo']}|Tomo {f['tomo']} — {vol.get(f['tomo'], f['titulo'])}|{rg}|{a}")
            js.append([carpeta, f["tomo"], "intro", rg, a])
        else:
            lineas.append(f"{carpeta}|{f['tomo']}|{f['titulo']}||{a}")
            js.append([carpeta, f["tomo"], f["cap"], f["titulo"], a])
    (INDICE / "titulos.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="\n")
    (INDICE / "indice_titulos.json").write_text(json.dumps(js, ensure_ascii=False), encoding="utf-8")
    return len(fichas)


def rango_tomo(fichas, intro):
    vv = [v for f in fichas if f["libro"] == intro["libro"] and f["tomo"] == intro["tomo"]
          and f["cap"] != "intro" for v in f["pasaje"]]
    if not vv:
        return ""
    vv.sort()
    return f"{vv[0][1]}:{vv[0][2]} – {vv[-1][1]}:{vv[-1][2]}"


if __name__ == "__main__":
    n = reconstruir_indice()
    print(f"Índice reconstruido: {n} archivos en {INDICE}")
