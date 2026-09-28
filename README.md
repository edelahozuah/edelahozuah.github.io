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
| Publicaciones (generado) | `_data/publicaciones.yml` |
| Correcciones a publicaciones | `_data/publicaciones_ajustes.yml` |
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
   laboratorio, retardos); si avisa de «sin familia», hay que enseñarle la nueva.
   `--quitar` deshace el cambio.
3. Guarda una captura de 720 px de ancho en `assets/img/recursos/`.
4. Añade una entrada en `_data/recursos.yml` (título, url, imagen, descripción,
   sesión y, si la hay, versión en inglés).

Aparece solo en la página de la asignatura y en `/recursos/`.

## Añadir una asignatura

1. Añade `pagina: /docencia/<id>/` a su entrada en `_data/asignaturas.yml`.
2. Copia `docencia/ar1/index.html` a `docencia/<id>/index.html` y cambia
   `title`, `permalink` y `asignatura`.
3. Añade sus temas y recursos en `_data/recursos.yml` bajo la clave `<id>`.

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
