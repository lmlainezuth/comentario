# Sesión en la nube: cómo escribir un tomo

Las variables de entorno no se conservan entre comandos: pon `LIBROS_LEVIN=...` delante de cada `python3`.

## 1. Preparar (una vez por sesión)

```
mkdir -p trabajo && unzip -o -q nube/biblia.zip -d trabajo && cp -r nube/trabajo/* trabajo/
LIBROS_LEVIN="$PWD/nube/libros levin" python3 preparar.py serie
```
Tiene que decir unos 1.920 archivos.

## 2. Escribir el tomo que pida el usuario

```
LIBROS_LEVIN="$PWD/nube/libros levin" nohup python3 orquestador.py tomo Juan 8 > trabajo/log.txt 2>&1 &
```
Tarda alrededor de una hora. Revisa `trabajo/log.txt` cada 10 minutos (líneas «guardado en» y «Tomo N terminado»).
Libro nuevo (por ejemplo Hechos): primero `orquestador.py plan Hechos` y el usuario revisa el plan antes de escribir.

## 3. Guardar y subir

```
mkdir -p nube/trabajo/Juan && cp trabajo/Juan/plan.json trabajo/Juan/brief-libro.md trabajo/Juan/estado.json nube/trabajo/Juan/
git add -A && git commit -m "Juan tomo 8" && git push
```
Los capítulos quedan en `nube/libros levin/<Libro>/capitulo N/`.
