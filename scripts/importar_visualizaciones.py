#!/usr/bin/env python3
"""Importa las visualizaciones desde el repositorio computer-networks-visualizations.

El repositorio es la fuente de verdad: allí se editan las visualizaciones y su
catálogo (catalog.yml). Este script, para cada recurso de _data/recursos.yml que
tenga «id»:

1. copia el HTML en español y en inglés del repositorio a las rutas «url» y
   «en» del recurso (las URL de la web no cambian aunque el repositorio
   renombre ficheros);
2. actualiza en _data/recursos.yml el título y la descripción en los dos
   idiomas con los del catálogo (edición textual, se conservan comentarios y
   orden);
3. reescribe _data/resumenes/visualizaciones.yml (resumen, conceptos y
   fórmulas por URL) y _data/visualizaciones.yml (URL → id, fichero del
   repositorio y versión), que usan scripts/estilo_visualizaciones.py y
   llms-full.txt;
4. ejecuta scripts/estilo_visualizaciones.py sobre las carpetas tocadas para
   añadir el estilo, la barra y los metadatos de la web.

Después comprueba que cada copia de la web, sin el estilo del sitio, coincide
con el fichero del repositorio.

Uso:
    python3 scripts/importar_visualizaciones.py            # ../Visualizaciones
    python3 scripts/importar_visualizaciones.py RUTA_REPO
    python3 scripts/importar_visualizaciones.py --comprobar  # solo verifica
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
from estilo_visualizaciones import quitar  # noqa: E402


def version_repo(repo):
    """Etiqueta o commit del repositorio, para _data/visualizaciones.yml."""
    try:
        return subprocess.run(["git", "-C", str(repo), "describe", "--tags", "--always", "--dirty"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def yaml_escalar(texto):
    """Representación YAML de una cadena en una línea (JSON es YAML válido)."""
    if re.search(r': | #|:$|^[-?:,\[\]{}#&*!|>\'"%@`]|^\s|\s$', texto) or texto.lower() in ("yes", "no", "true", "false", "null", "~"):
        return json.dumps(texto, ensure_ascii=False)
    return texto


def actualizar_recursos(ruta, cambios):
    """cambios: {id: {clave: valor}} → edita en el texto el bloque de cada
    recurso con ese id. Devuelve el número de líneas cambiadas."""
    lineas = ruta.read_text(encoding="utf-8").split("\n")
    # Bloques: cada recurso empieza en una línea «      - titulo:» (u otra clave) y
    # dura hasta la siguiente de la misma sangría que empiece por «-» o una menor.
    inicio = {}  # índice de línea → id
    for i, l in enumerate(lineas):
        m = re.match(r"(\s+)id: (\S+)\s*$", l)
        if m and m.group(2) in cambios:
            sangria = len(m.group(1))
            j = i
            while j > 0 and not re.match(r"\s{%d}- " % (sangria - 2), lineas[j]):
                j -= 1
            inicio[j] = (m.group(2), sangria)
    n = 0
    for j, (id_, sangria) in inicio.items():
        k = j + 1
        while k < len(lineas) and lineas[k].strip() and not re.match(r"\s{0,%d}\S" % (sangria - 1), lineas[k]) \
                and not re.match(r"\s{%d}- " % (sangria - 2), lineas[k]):
            k += 1
        for i in range(j, k):
            m = re.match(r"(\s+)(titulo|titulo_en|descripcion|descripcion_en): ", lineas[i]) or \
                (re.match(r"(\s+)- (titulo): ", lineas[i]) if i == j else None)
            if m and m.group(2) in cambios[id_]:
                pref = lineas[i][:m.end()]
                nueva = pref + yaml_escalar(cambios[id_][m.group(2)])
                if nueva != lineas[i]:
                    lineas[i] = nueva
                    n += 1
    ruta.write_text("\n".join(lineas), encoding="utf-8")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", nargs="?", default=str(RAIZ.parent / "Visualizaciones"))
    ap.add_argument("--comprobar", action="store_true", help="no copia nada; verifica que la web coincide con el repositorio")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    catalogo = yaml.safe_load((repo / "catalog.yml").read_text(encoding="utf-8"))
    viz = {v["id"]: v for v in catalogo["visualizations"]}
    recursos = yaml.safe_load((RAIZ / "_data" / "recursos.yml").read_text(encoding="utf-8"))

    pares, cambios, resumenes, mapa, carpetas, errores = [], {}, {}, {}, set(), []
    for temas in recursos.values():
        for t in temas:
            for r in t.get("recursos", []):
                if not r.get("id"):
                    continue
                v = viz.get(r["id"])
                if not v:
                    errores.append(f"{r['url']}: id {r['id']} no está en catalog.yml")
                    continue
                if not r.get("en"):
                    errores.append(f"{r['url']}: falta «en» (el catálogo tiene las dos versiones)")
                    continue
                for lang, url in (("es", r["url"]), ("en", r["en"])):
                    pares.append((repo / v["files"][lang], RAIZ / url.lstrip("/"), url))
                    resumenes[url] = {"resumen": v["summary"][lang], "conceptos": v["concepts"][lang]}
                    if v.get("formulas"):
                        resumenes[url]["formulas"] = v["formulas"][lang]
                    mapa[url] = {"id": r["id"], "fichero": v["files"][lang], "idioma": lang}
                    carpetas.add(str(Path(url.lstrip("/")).parent))
                cambios[r["id"]] = {"titulo": v["title"]["es"], "titulo_en": v["title"]["en"],
                                    "descripcion": v["description"]["es"], "descripcion_en": v["description"]["en"]}
    if errores:
        print("\n".join(errores))
        sys.exit(1)

    if args.comprobar:
        mal = 0
        for origen, destino, url in pares:
            if not destino.exists():
                print(f"  falta       {url}"); mal += 1
            elif quitar(destino.read_text(encoding="utf-8")) != origen.read_text(encoding="utf-8"):
                print(f"  difiere     {url}  ≠  {origen.relative_to(repo)}"); mal += 1
        print(f"{len(pares) - mal} copias coinciden con el repositorio" + (f", {mal} no" if mal else ""))
        sys.exit(1 if mal else 0)

    for origen, destino, url in pares:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(origen.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  copiado     {url}  ←  {origen.relative_to(repo)}")
    n = actualizar_recursos(RAIZ / "_data" / "recursos.yml", cambios)
    print(f"  recursos.yml: {n} títulos o descripciones actualizados")

    cab = ("# Generado por scripts/importar_visualizaciones.py a partir de catalog.yml del\n"
           "# repositorio computer-networks-visualizations. No editar a mano: los textos se\n"
           "# corrigen en el catálogo del repositorio. Lo usan scripts/estilo_visualizaciones.py\n"
           "# (texto estático y JSON-LD de cada visualización) y llms-full.txt.\n\n")
    class D(yaml.SafeDumper):
        pass
    D.add_representer(str, lambda d, s: d.represent_scalar("tag:yaml.org,2002:str", s, style=">" if len(s) > 100 else None))
    (RAIZ / "_data" / "resumenes").mkdir(exist_ok=True)
    (RAIZ / "_data" / "resumenes" / "visualizaciones.yml").write_text(
        cab + yaml.dump(resumenes, Dumper=D, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")
    conf = yaml.safe_load((RAIZ / "_config.yml").read_text(encoding="utf-8")).get("visualizaciones", {})
    datos = {"repositorio": conf.get("repo"), "pages": conf.get("pages"), "version": version_repo(repo), "visualizaciones": mapa}
    (RAIZ / "_data" / "visualizaciones.yml").write_text(
        "# Generado por scripts/importar_visualizaciones.py: de qué fichero del repositorio\n"
        "# computer-networks-visualizations viene cada visualización de la web y con qué\n"
        "# versión se importó. Lo usa scripts/estilo_visualizaciones.py (enlace al original\n"
        "# en el pie y sameAs del JSON-LD). No editar a mano.\n\n"
        + yaml.dump(datos, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print("  _data/resumenes/visualizaciones.yml y _data/visualizaciones.yml regenerados")
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "estilo_visualizaciones.py"), *sorted(carpetas)], check=True)
    for origen, destino, url in pares:
        if quitar(destino.read_text(encoding="utf-8")) != origen.read_text(encoding="utf-8"):
            print(f"  AVISO: {url} no coincide con el repositorio tras aplicar el estilo")


if __name__ == "__main__":
    main()
