<!--
Versao: 1.0.0
Data de criacao: 2026-08-10
Data da ultima modificacao: 2026-08-10
-->

# Informe de Metadata — Guia Rapida

Herramienta para regenerar informes HTML y vectorizar vuelos a partir de JSONs temporales generados por el pipeline de metadatos.

La lista de JSONs disponibles se carga automaticamente desde la carpeta temporal de informes, ordenada del mas reciente al mas antiguo.

## Lo que hace la herramienta

- **Generar informe** — genera un informe HTML a partir del JSON seleccionado y abre el archivo automaticamente.
- **Vectorizar vuelo** — crea una capa de puntos (`Flight_...`) a partir del JSON y genera la capa de rastro (linea) correspondiente.
- **Boton de actualizar** — actualiza la lista de JSONs temporales disponibles.
- **Abrir carpetas** — abre la carpeta de JSONs temporales o la carpeta de informes HTML.

## Como usar

1. Abra `Cadmus > Informe de Metadata`.
2. Seleccione un archivo JSON temporal de la lista (del mas reciente al mas antiguo).
3. Elija una accion:
   - Haga clic en `Generar Informe` para generar y abrir el informe HTML.
   - Haga clic en `Vectorizar Vuelo` para crear las capas de puntos y rastro en el proyecto.
4. Use los botones auxiliares si es necesario:
   - `Actualizar lista` — recarga los JSONs disponibles.
   - `Abrir carpeta de JSONs` — abre la carpeta donde se guardan los archivos JSON temporales.
   - `Abrir carpeta de informes` — abre la carpeta donde se guardan los informes HTML generados.

## Lo que el plugin hace realmente

- Lee los archivos `.json` de la carpeta temporal de informes (`REPORTS_TEMP_FOLDER` + `REPORTS_JSON_FOLDER`), ordenados por fecha de modificacion (mas reciente primero).
- El combo muestra el nombre de cada archivo JSON; la seleccion se guarda en las preferencias de la herramienta.
- **Generar informe**:
  - Valida que se haya seleccionado un JSON y que el archivo exista.
  - Verifica que la licencia tenga nivel minimo 3 (`RegistryManager.has_minimum_level`).
  - Usa `ReportGenerationService.generate_from_json()` para generar el HTML y obtiene la ruta del payload.
  - Abre el HTML automaticamente con `ExplorerUtils.open_file()`.
- **Vectorizar vuelo**:
  - Usa `JsonToVectorTranslator.translate()` para crear la capa de puntos.
  - El nombre de la capa es `Flight_<titulo>` (campo `titulo` del JSON) o `Flight_<nombre del archivo>` como respaldo.
  - La fuente de coordenadas se lee del campo `source` del JSON (predeterminado `mrk+photo`).
  - Los campos de la capa se reordenan alfabeticamente.
  - La capa de puntos se agrega al proyecto.
  - Genera la capa de rastro (linea) a partir de los puntos, ordenada por campo de foto (Foto/PhotoNum/id) y agrupada por `MrkPath` + `MrkFile`.
  - Muestra en la barra: `Vuelo vectorizado: N puntos y rastro generados.`

## Comportamiento importante

- Generar un informe requiere licencia nivel 3 o superior; sin ella, la herramienta muestra un aviso.
- Si no se selecciona ningun JSON o el archivo no existe, la herramienta muestra un aviso (`Seleccione un archivo` / `Archivo no encontrado`).
- La lista de JSONs puede estar vacia — use `Actualizar lista` despues de generar nuevos JSONs en el pipeline.
- El informe HTML generado se abre automaticamente; si falla al abrir, se muestra una barra de aviso.
- El JSON temporal contiene los metadatos del vuelo (titulo, fuente de coordenadas, fotos y marcas) usados tanto por el informe como por la vectorizacion.

## Cuando usarla

Use esta herramienta cuando quiera:

- regenerar un informe HTML de un vuelo sin reprocesar todo el pipeline;
- vectorizar un vuelo ya procesado, recreando las capas de puntos y rastro;
- acceder rapidamente a las carpetas de JSONs temporales y de informes HTML.

## Cuidados

- La vectorizacion agrega capas al proyecto — verifique que no existan capas con el mismo nombre.
- Generar un informe abre el HTML en el navegador; compruebe que la carpeta de informes exista.
- La lista de JSONs solo se actualiza manualmente (boton `Actualizar lista`) o al abrir la herramienta.
- Licenciamiento: generar informes requiere nivel 3; la vectorizacion no exige ese nivel.