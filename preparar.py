"""
Construye trabajo/biblia.db con todo lo que el comentario consulta, sin internet ni Supabase.
Se ejecuta una vez (y otra cuando se añadan libros a la serie: python preparar.py --serie).
"""
import csv, json, re, sqlite3, sys
from config import DB, DESCARGAS, ASSETS, TRABAJO
from comun import LIBROS, ORDEN, norm
import serie

LXX_COD = {"GEN": 1, "EXO": 2, "LEV": 3, "NUM": 4, "DEU": 5, "JOS": 6, "JDG": 7, "RUT": 8, "1SA": 9,
           "2SA": 10, "1KI": 11, "2KI": 12, "1CH": 13, "2CH": 14, "EZR": 15, "ESG": 17, "JOB": 18,
           "PSA": 19, "PRO": 20, "ECC": 21, "ISA": 23, "JER": 24, "LAM": 25, "EZE": 26, "DNG": 27,
           "HOS": 28, "JOE": 29, "AMO": 30, "OBA": 31, "JON": 32, "MIC": 33, "NAH": 34, "HAB": 35,
           "ZEP": 36, "HAG": 37, "ZEC": 38, "MAL": 39}


def cargar_json(ruta):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def biblia(con, tabla, archivo):
    ruta = DESCARGAS / "biblias" / archivo
    if not ruta.exists():
        print(f"  falta {ruta}")
        return
    filas = [(ORDEN.get(f["libro"]), f["cap"], f["vers"], f["texto"], norm(f["texto"]))
             for f in cargar_json(ruta)]
    malos = {f["libro"] for f in cargar_json(ruta) if f["libro"] not in ORDEN}
    if malos:
        print("  libros sin reconocer:", malos)
    con.executemany(f"insert into {tabla} values (?,?,?,?,?)", [f for f in filas if f[0]])
    print(f"  {tabla}: {len(filas)} versículos")


def originales(con):
    filas = []
    for lo in range(1, 67):
        ruta = ASSETS / f"{lo}.tsv"
        if not ruta.exists():
            continue
        with open(ruta, encoding="utf-8") as fh:
            for linea in fh:
                partes = linea.rstrip("\n").split("\t")
                if len(partes) < 3:
                    continue
                cap, ver = int(partes[0]), int(partes[1])
                for pos, p in enumerate(partes[2:], 1):
                    w = (p.split("|") + ["", "", "", ""])[:4]
                    for s in re.findall(r"[HG]\d+", w[2]) or [""]:
                        filas.append((lo, cap, ver, pos, w[0], w[1], s, w[3]))
    con.executemany("insert into orig values (?,?,?,?,?,?,?,?)", filas)
    print(f"  orig (TAHOT/TAGNT): {len(filas)} palabras")


def strong(con):
    ruta = DESCARGAS / "datos" / "strong_diccionario.json"
    if not ruta.exists():
        print("  falta datos/strong_diccionario.json (python descargar_tablas.py strong_diccionario)")
        return
    filas = []
    for f in cargar_json(ruta):
        pre = "H" if str(f.get("idioma", "")).lower().startswith("h") else "G"
        num = re.sub(r"\D", "", str(f["numero"]))
        filas.append((pre + num, f.get("lemma"), f.get("pronunciacion"), f.get("definicion")))
    con.executemany("insert or replace into strong values (?,?,?,?)", filas)
    print(f"  strong: {len(filas)} fichas")


def lxx(con):
    ruta = DESCARGAS / "originales" / "lxx_brenton.tsv"
    if not ruta.exists():
        print("  falta originales/lxx_brenton.tsv")
        return
    filas = []
    with open(ruta, encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            lo = LXX_COD.get(r["libro"])
            if lo:
                filas.append((lo, int(r["capitulo"]), int(r["versiculo"]), r["texto"]))
    con.executemany("insert into lxx values (?,?,?,?)", filas)
    print(f"  lxx (numeración griega): {len(filas)}")


def sefaria(con):
    ruta = DESCARGAS / "originales" / "tanaj_sefaria.tsv"
    if not ruta.exists():
        print("  falta originales/tanaj_sefaria.tsv")
        return
    with open(ruta, encoding="utf-8") as fh:
        filas = [(int(r["orden"]), int(r["capitulo"]), int(r["versiculo"]), r["texto"])
                 for r in csv.DictReader(fh, delimiter="\t")]
    con.executemany("insert into sefaria values (?,?,?,?)", filas)
    print(f"  sefaria (numeración hebrea): {len(filas)}")


def titulos(con):
    ruta = DESCARGAS / "titulos" / "titulos_biblia.json"
    if not ruta.exists():
        return
    filas = [(ORDEN.get(f["libro"]), f["capitulo"], f["versiculo_inicio"], f["versiculo_fin"], f["titulo"])
             for f in cargar_json(ruta)]
    con.executemany("insert into titulos values (?,?,?,?,?)", [f for f in filas if f[0]])
    print(f"  titulos: {len(filas)}")


def cruzadas(con):
    d = DESCARGAS / "datos"
    rutas = [d / "referencias_cruzadas.json", d / "capitulos.json", d / "libros.json"]
    if not all(r.exists() for r in rutas):
        print("  referencias cruzadas: faltan datos/capitulos.json o libros.json (python descargar_tablas.py)")
        return
    libros = {l["id"]: ORDEN.get(l["nombre"]) for l in cargar_json(rutas[2])}
    caps = {c["id"]: (libros.get(c["libro_id"]), c["numero"]) for c in cargar_json(rutas[1])}
    filas = []
    for r in cargar_json(rutas[0]):
        a, b = caps.get(r["desde_capitulo_id"]), caps.get(r["hacia_capitulo_id"])
        if a and b and a[0] and b[0]:
            filas.append((a[0], a[1], r["desde_versiculo"], b[0], b[1], r["hacia_versiculo_inicio"],
                          r["hacia_versiculo_fin"], r.get("votos") or 0))
    con.executemany("insert into cruzadas values (?,?,?,?,?,?,?,?)", filas)
    print(f"  referencias cruzadas: {len(filas)}")


def cargar_serie(con):
    fichas = serie.todas()
    for i, f in enumerate(fichas):
        con.execute("insert into serie values (?,?,?,?,?,?,?,?)",
                    (i, f["libro"], f["tomo"], str(f["cap"]), f["titulo"], f["archivo"], f["ruta"],
                     norm(f["texto"])))
        con.executemany("insert into pasajes values (?,?,?,?)", [(lo, c, v, i) for lo, c, v in f["pasaje"]])
    print(f"  serie: {len(fichas)} archivos escritos")


ESQUEMA = """
create table if not exists rvr(lo, cap, ver, texto, n);
create table if not exists rvp(lo, cap, ver, texto, n);
create table if not exists orig(lo, cap, ver, pos, palabra, translit, strong, glosa);
create table if not exists strong(num primary key, lemma, pron, def);
create table if not exists lxx(lo, cap, ver, texto);
create table if not exists sefaria(lo, cap, ver, texto);
create table if not exists titulos(lo, cap, vi, vf, titulo);
create table if not exists cruzadas(lo, cap, ver, lo2, cap2, v2i, v2f, votos);
create table if not exists serie(id, libro, tomo, cap, titulo, archivo, ruta, n);
create table if not exists pasajes(lo, cap, ver, serie_id);
"""
INDICES = """
create index if not exists i_rvr on rvr(lo, cap, ver);
create index if not exists i_rvp on rvp(lo, cap, ver);
create index if not exists i_orig on orig(lo, cap, ver);
create index if not exists i_orig_s on orig(strong);
create index if not exists i_lxx on lxx(lo, cap, ver);
create index if not exists i_sef on sefaria(lo, cap, ver);
create index if not exists i_cru on cruzadas(lo, cap, ver);
create index if not exists i_pas on pasajes(lo, cap, ver);
"""


PASOS = {
    "biblias": (["rvr", "rvp"], lambda con: (biblia(con, "rvr", "RVR1960.json"), biblia(con, "rvp", "RV1960plus.json"))),
    "orig": (["orig"], originales),
    "extra": (["strong", "lxx", "sefaria", "titulos", "cruzadas"],
              lambda con: (strong(con), lxx(con), sefaria(con), titulos(con), cruzadas(con))),
    "serie": (["serie", "pasajes"], cargar_serie),
}


def main():
    """python preparar.py            -> todo
       python preparar.py serie      -> solo rehacer la serie (tras escribir un tomo)"""
    TRABAJO.mkdir(parents=True, exist_ok=True)
    pasos = [a for a in sys.argv[1:] if a in PASOS] or list(PASOS)
    con = sqlite3.connect(str(DB))
    con.executescript(ESQUEMA)
    print("Preparando", DB, flush=True)
    for p in pasos:
        tablas, fn = PASOS[p]
        for t in tablas:
            con.execute(f"delete from {t}")
        con.commit()
        fn(con)
        con.commit()
    con.executescript(INDICES)
    con.commit(); con.close()
    print("Listo.")


if __name__ == "__main__":
    main()
