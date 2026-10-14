"""
Consultas locales para escribir el comentario (sin internet ni Supabase).

  python biblia.py ver "Isaías 1:1-9"        texto RVR1960
  python biblia.py plus "Isaías 1:18"        RV1960+ con números Strong
  python biblia.py heb "Isaías 1:18"         hebreo/griego palabra por palabra (TAHOT/TAGNT, numeración RVR)
  python biblia.py strong H8141              ficha y todos los versículos donde está (recuento del original)
  python biblia.py con H2530 H6529           versículos que tienen todos esos números
  python biblia.py busca "lavaos y limpiaos" dónde está una frase en la RVR1960
  python biblia.py serie "sombra del deseado" dónde se trató ya en los libros escritos
  python biblia.py pasaje "Salmos 45:7"      qué capítulo de la serie tiene ese versículo como texto principal
  python biblia.py cruzadas "Isaías 53:5"    referencias cruzadas más votadas
  python biblia.py lxx "Isaías 7:14"         Septuaginta (Brenton; numeración griega; dato de fuera)
  python biblia.py sefaria "Malaquías 3:19"  hebreo de Sefaria (numeración hebrea)
  python biblia.py titulos "Isaías 1"        títulos de sección de la RVR
"""
import re, sys
from comun import db, parse_ref, LIBROS, ORDEN, norm

NOMBRE = {i + 1: l for i, l in enumerate(LIBROS)}


def ref(lo, cap, ver):
    return f"{NOMBRE[lo]} {cap}:{ver}"


def pedir_ref(texto):
    libro, vv = parse_ref(texto)
    if not vv:
        # "Isaías 1" = capítulo entero
        m = re.match(r"(.+?)\s+(\d+)$", texto.strip())
        from comun import libro_canonico
        if m and libro_canonico(m.group(1)):
            lo = ORDEN[libro_canonico(m.group(1))]
            vv = [(lo, int(m.group(2)), v) for (v,) in
                  db().execute("select ver from rvr where lo=? and cap=? order by ver", (lo, int(m.group(2))))]
    if not vv:
        sys.exit(f"No entiendo la referencia: {texto}")
    return vv


def ver(t, tabla="rvr"):
    for lo, c, v in pedir_ref(t):
        r = db().execute(f"select texto from {tabla} where lo=? and cap=? and ver=?", (lo, c, v)).fetchone()
        print(f"{ref(lo, c, v)}  {r[0] if r else '(no existe)'}")


def heb(t):
    for lo, c, v in pedir_ref(t):
        r = db().execute("select texto from rvr where lo=? and cap=? and ver=?", (lo, c, v)).fetchone()
        print(f"\n{ref(lo, c, v)}  {r[0] if r else ''}")
        filas = db().execute("select pos, palabra, translit, group_concat(strong,'/'), glosa from orig "
                             "where lo=? and cap=? and ver=? group by pos order by pos", (lo, c, v)).fetchall()
        print("  " + "  ".join(f"{p} {tr} ({s}){' ' + g if g else ''}" for _, p, tr, s, g in filas))


def ficha(num):
    r = db().execute("select lemma, pron, def from strong where num=?", (num,)).fetchone()
    return f"{num} {r[0]} ({r[1]}): {r[2]}" if r else f"{num}: sin ficha en strong_diccionario"


def strong(num, limite=150):
    num = num.upper()
    print(ficha(num))
    filas = db().execute("select lo, cap, ver, group_concat(palabra, ' ') from orig where strong=? "
                         "group by lo, cap, ver order by lo, cap, ver", (num,)).fetchall()
    print(f"En el original (TAHOT/TAGNT): {len(filas)} versículos")
    for lo, c, v, p in filas[:limite]:
        print(f"  {ref(lo, c, v)}  {p}")
    if len(filas) > limite:
        print(f"  … y {len(filas) - limite} más")


def con(nums):
    nums = [n.upper() for n in nums]
    q = " intersect ".join(["select lo, cap, ver from orig where strong=?"] * len(nums))
    filas = db().execute(q + " order by 1,2,3", nums).fetchall()
    print(f"{' + '.join(nums)}: {len(filas)} versículos")
    for lo, c, v in filas:
        print("  " + ref(lo, c, v))


def busca(frase, limite=60):
    n = norm(frase)
    filas = db().execute("select lo, cap, ver, texto from rvr where n like ? order by lo, cap, ver",
                         (f"%{n}%",)).fetchall()
    print(f"«{frase}»: {len(filas)} versículos")
    for lo, c, v, t in filas[:limite]:
        print(f"  {ref(lo, c, v)}  {t}")


def serie(frase, limite=25):
    n = norm(frase)
    filas = db().execute("select libro, tomo, cap, titulo, ruta from serie where n like ?", (f"%{n}%",)).fetchall()
    print(f"«{frase}» en la serie: {len(filas)} archivos")
    for libro, tomo, cap, titulo, ruta in filas[:limite]:
        donde = f"{libro}, tomo {tomo}, " + ("introducción" if cap == "intro" else f"capítulo {cap}")
        trozo = ""
        try:
            txt = open(ruta, encoding="utf-8").read()
            i = norm(txt).find(n)
            # posición aproximada: buscar la primera palabra en el texto original
            palabra = frase.split()[0]
            j = txt.lower().find(palabra.lower())
            if j >= 0:
                trozo = txt[max(0, j - 120): j + 200].replace("\n", " ")
        except OSError:
            pass
        print(f"- {donde} (*{titulo}*)\n    …{trozo}…")


def pasaje(t):
    for lo, c, v in pedir_ref(t):
        filas = db().execute("select distinct s.libro, s.tomo, s.cap, s.titulo from pasajes p join serie s "
                             "on s.id=p.serie_id where p.lo=? and p.cap=? and p.ver=?", (lo, c, v)).fetchall()
        if not filas:
            print(f"{ref(lo, c, v)}: ningún capítulo de la serie lo tiene como texto principal")
        for libro, tomo, cap, titulo in filas:
            print(f"{ref(lo, c, v)}: {libro}, tomo {tomo}, capítulo {cap} (*{titulo}*)")


def cruzadas(t, limite=25):
    for lo, c, v in pedir_ref(t):
        filas = db().execute("select lo2, cap2, v2i, v2f, votos from cruzadas where lo=? and cap=? and ver=? "
                             "order by votos desc limit ?", (lo, c, v, limite)).fetchall()
        print(f"{ref(lo, c, v)}:")
        for lo2, c2, a, b, votos in filas:
            print(f"  {NOMBRE[lo2]} {c2}:{a}{'-' + str(b) if b and b != a else ''}  ({votos})")


def titulos(t):
    m = re.match(r"(.+?)\s+(\d+)$", t.strip())
    from comun import libro_canonico
    lo = ORDEN[libro_canonico(m.group(1))]
    for c, vi, vf, tit in db().execute("select cap, vi, vf, titulo from titulos where lo=? and cap=? order by vi",
                                       (lo, int(m.group(2)))):
        print(f"{c}:{vi}{'-' + str(vf) if vf else ''}  {tit}")


def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    cmd, args = sys.argv[1], sys.argv[2:]
    {"ver": lambda: ver(args[0]), "plus": lambda: ver(args[0], "rvp"), "heb": lambda: heb(args[0]),
     "strong": lambda: strong(args[0]), "con": lambda: con(args), "busca": lambda: busca(" ".join(args)),
     "serie": lambda: serie(" ".join(args)), "pasaje": lambda: pasaje(args[0]),
     "cruzadas": lambda: cruzadas(args[0]), "lxx": lambda: ver(args[0], "lxx"),
     "sefaria": lambda: ver(args[0], "sefaria"), "titulos": lambda: titulos(args[0]),
     }.get(cmd, lambda: print(__doc__))()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
