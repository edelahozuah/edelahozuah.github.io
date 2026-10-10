# edelahozuah.github.io

Web personal de Enrique de la Hoz (Universidad de Alcalá): docencia, recursos
docentes e investigación. Jekyll publicado con GitHub Pages; no hay paso de
compilación propio.

## Estructura

| Qué | Dónde |
|---|---|
| Datos personales, menú | `_config.yml` |
| Asignaturas | `_data/asignaturas.yml` |
| Recursos docentes (índice) | `_data/recursos.yml` |
| Recursos docentes (los HTML) | `docencia/<asignatura>/<tema>/` |
| Miniaturas de los recursos | `assets/img/recursos/` |
| Noticias de la portada | `_data/noticias.yml` |
| Líneas de investigación | `_data/lineas.yml` |
| Proyectos de investigación (IP) | `_data/proyectos_investigacion.yml` |
| Publicaciones (generado) | `_data/publicaciones.yml` |
| Correcciones a publicaciones | `_data/publicaciones_ajustes.yml` |
| Resúmenes de las visualizaciones | `_data/resumenes/*.yml` |
| Vídeos de YouTube (una página por vídeo e idioma) | `_videos/<asignatura>/` |
| Trabajos dirigidos (TFM y TFG) | `_data/trabajos.yml` |
| Proyectos docentes (herramientas y datos abiertos) | `_data/proyectos.yml` |
| Metadatos y JSON-LD de las páginas | `_includes/metadatos.html`, `_includes/jsonld.html` |
| Versión para modelos de lenguaje | `llms.txt`, `llms-full.txt` |
| Estilos (aspecto al-folio) | `assets/css/sitio.css` |

El aspecto sigue las convenciones del tema [al-folio](https://github.com/alshedivat/al-folio).
El color de acento es la variable `--global-theme-color` de `assets/css/sitio.css`.

## Añadir un recurso

1. Copia el HTML autocontenido en `docencia/<asignatura>/<tema>/`, por ejemplo
   `docencia/ar1/tcp/ventana.html`. Sin cabecera YAML: Jekyll lo publica tal cual.
2. Adáptala al aspecto de la web:
   `python3 scripts/estilo_visualizaciones.py docencia/ar1/tcp`. Añade la barra
   superior y cambia fondo, tipografía y acento sin tocar los colores con
   significado. Reconoce las familias de estilo existentes (DNS, capas/colas,
   laboratorio, retardos, diagrama de retardos); si avisa de «sin familia», hay
   que enseñarle la nueva.
   `--quitar` deshace el cambio.
3. Guarda una captura de 720 px de ancho en `assets/img/recursos/`.
4. Añade una entrada en `_data/recursos.yml` (título, url, imagen, descripción,
   sesión y, si la hay, versión en inglés).
5. Escribe su resumen en `_data/resumenes/` (uno por idioma, con la URL como
   clave): `resumen` (3–5 frases), `conceptos` y, si las hay, `formulas`.
6. Vuelve a ejecutar el script del paso 2: con los datos de los pasos 4 y 5
   añade a la visualización su descripción, URL canónica, `hreflang`, Open
   Graph y JSON-LD, y un bloque final «Sobre esta visualización» en texto
   estático. Es idempotente; ejecútalo cada vez que cambies esos datos.

Aparece solo en la página de la asignatura y en `/recursos/`.

## Añadir un vídeo de YouTube

El vídeo sigue alojado en YouTube: la web tiene una página por vídeo con el
reproductor incrustado (youtube-nocookie), los capítulos, las visualizaciones
relacionadas, la transcripción y los datos estructurados `VideoObject`.

1. Genera las páginas (lee de YouTube la ficha y los subtítulos, sin descargar
   el vídeo; necesita yt-dlp y Node.js):

   ```sh
   python3 -m venv /tmp/yt && /tmp/yt/bin/pip install yt-dlp pyyaml
   /tmp/yt/bin/python scripts/importar_video.py URL --asignatura ar1 \
     --slug nombre-en-espanol --slug-en name-in-english --sesion 1.3
   ```

   Los capítulos salen de las marcas de tiempo de la descripción del vídeo.
   Si hay subtítulos en inglés, crea también la página inglesa.
2. Revisa el front matter de `_videos/<asignatura>/*.md`: título, descripción
   y capítulos en inglés (los marcados con TRADUCIR) y, si quieres,
   `relacionados:` con las URL de las visualizaciones del mismo tema.
3. Revisa la transcripción: los subtítulos generados por voz traen erratas.
4. Pega en `_data/recursos.yml` la entrada que imprime el script (con
   `tipo: video`) para que el vídeo salga en su tema.

## Añadir una asignatura

1. Añade `pagina: /docencia/<id>/` a su entrada en `_data/asignaturas.yml`.
2. Copia `docencia/ar1/index.html` a `docencia/<id>/index.html` y cambia
   `title`, `permalink` y `asignatura`.
3. Añade sus temas y recursos en `_data/recursos.yml` bajo la clave `<id>`.

## Añadir un proyecto docente

Los proyectos docentes son herramientas y datos abiertos de uso general, no
ligados a una asignatura (por ejemplo, los horarios de la EPS en datos abiertos).
Salen en `/docencia/proyectos/` y `/en/teaching/projects/`, en la lista de
`/docencia/`, en `llms.txt` y `llms-full.txt`, y como `SoftwareApplication` y
`Dataset` en el JSON-LD de la página.

1. Añade una entrada en `_data/proyectos.yml` (los campos están comentados en
   el fichero; los textos en inglés son obligatorios porque la página inglesa
   muestra todos los proyectos).
2. Guarda una captura de 1200×630 en `assets/img/` y ponla en `imagen:`.
   Por ejemplo, con Chrome:
   `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --window-size=1200,630 --virtual-time-budget=8000 --screenshot=captura.png URL`
3. Si publica datos, lista los ficheros en `datos:` con su número de filas;
   hay que actualizarlo cuando se regeneren.
4. Añade una noticia en `_data/noticias.yml`.

## Páginas en inglés

Cada página en español tiene su pareja bajo `/en/`, con front matter
`lang: en` y `lang_alt: <url de la pareja en el otro idioma>` (el conmutador
«es/en» de la cabecera usa ese campo). Los textos largos (bio, líneas de
investigación) están duplicados en cada página; los textos cortos que vienen
de `_data/` usan un campo `_en` o `en` junto al original:

| Fichero | Campo en español | Su pareja en inglés |
|---|---|---|
| `_data/asignaturas.yml` | `nombre`, `pagina`, `nivel` | `nombre_en`, `pagina_en`, `nivel_en` |
| `_data/recursos.yml` | `titulo`, `descripcion`, `etiqueta` | `titulo_en`, `descripcion_en`, `etiqueta_en` |
| `_data/lineas.yml` | `titulo`, `texto` | `en`, `texto_en` |
| `_data/noticias.yml` | `texto` | `texto_en` (si falta, la noticia no sale en inglés) |

Un recurso de `_data/recursos.yml` solo aparece en las páginas en inglés si
tiene `en:` (la ruta de su HTML traducido). Si una visualización no tiene
traducción, no hace falta añadir sus campos `_en`; simplemente no sale en
`/en/`. `scripts/estilo_visualizaciones.py` añade además, dentro de cada
visualización, el enlace de vuelta a su pareja en el otro idioma (lo calcula
solo con el campo `en:` de `_data/recursos.yml`, así que basta con rellenarlo
y volver a ejecutar el script).

## Actualizar las publicaciones

```sh
python3 scripts/actualizar_publicaciones.py
```

Lee ORCID (trabajos, DOI, autores) y Google Scholar (citas, índice h), fusiona
los duplicados y reescribe `_data/publicaciones.yml` y `_data/metricas.yml`.
Necesita PyYAML. Si Scholar bloquea la petición, conserva las citas anteriores;
`--sin-scholar` se salta Scholar a propósito.

No edites `_data/publicaciones.yml` a mano: las correcciones (ocultar
duplicados, cambiar tipo o título, destacar en portada, enlazar un PDF, añadir
trabajos que no estén en ORCID) van en `_data/publicaciones_ajustes.yml`, que el
script aplica en cada ejecución.

## Buscadores y modelos de lenguaje

- `_includes/metadatos.html` pone en cada página el título, la descripción
  (`description:` del front matter, en su idioma), la URL canónica, `hreflang`
  (con `lang_alt:`), Open Graph (`imagen:` para la imagen de compartir) y el
  JSON-LD de `_includes/jsonld.html`: la persona y el sitio en todas; las
  publicaciones con `jsonld: publicaciones`; la asignatura y sus recursos con
  `asignatura:` (y `carpeta:` para limitarlos a un tema); todos los recursos
  con `jsonld: recursos`. El `h1` visible es `cabecera:` si existe, y si no
  `title:`.
- `llms.txt` y `llms-full.txt` se generan desde `_data/`, así que se
  actualizan solos al añadir recursos, resúmenes o publicaciones.
- `robots.txt` permite el rastreo a todos los agentes, también a los de IA.

## Estadísticas de acceso

Las visitas se cuentan con [GoatCounter](https://edelahozuah.goatcounter.com),
sin cookies ni datos personales, por lo que no hace falta banner de
consentimiento. La URL del contador está en `_config.yml` (`goatcounter`);
`_layouts/base.html` la inserta en las páginas de Jekyll y
`scripts/estilo_visualizaciones.py` en las visualizaciones autocontenidas. El
panel muestra las visitas por página (cada visualización, ficha de vídeo o
tema es una URL) y las descargas de PDF de publicaciones, que se registran como
eventos al pulsar el enlace (`data-goatcounter-click`). Cada visualización
envía además un evento `uso:<ruta>` la primera vez que el visitante pulsa un
control, mueve un deslizador o teclea (sin contar la barra del sitio ni el
bloque «Sobre esta visualización»): comparar «uso:» con las visitas de la
misma ruta distingue quién solo abre la página de quién la usa. Si se cambia o quita la
URL hay que volver a ejecutar el script sobre `docencia/`.

## Ver la web en local

Con Docker, usando las mismas versiones que GitHub Pages:

```sh
docker run --rm -it -p 4000:4000 -v "$PWD":/srv -w /srv ruby:3.3 \
  bash -c "bundle config set path vendor/bundle && bundle install && bundle exec jekyll serve --host 0.0.0.0"
```

y abre <http://localhost:4000>.

## Licencia

Los materiales docentes (todo lo que hay en `docencia/`) se publican con
licencia [Creative Commons Reconocimiento-CompartirIgual 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.es)
(CC BY-SA 4.0). El aviso aparece en el pie de todas las páginas.
