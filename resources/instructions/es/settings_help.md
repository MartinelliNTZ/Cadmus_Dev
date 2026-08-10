<!--
Versao: 1.0.0
Data de criacao: 2026-08-10
Data da ultima modificacao: 2026-08-10
-->

# Configuraciones de Cadmus — Guia Rapida

Esta herramienta centraliza preferencias globales usadas por partes del plugin Cadmus.

En el estado actual del codigo, permite:

- definir la carpeta raiz de proyectos de Cadmus;
- elegir el SRC (sistema de referencia de coordenadas) predeterminado;
- definir el idioma de la interfaz (o auto-detectar el de QGIS);
- elegir el metodo predeterminado de calculo vectorial (Elipsoidal, Cartesiano, Ambos);
- definir los sufijos de los campos de area cartesiana y elipsoidal;
- definir la precision numerica de campos vectoriales;
- definir el umbral de entidades para procesamiento asincrono;
- controlar que categorias de herramientas aparecen en la barra de herramientas;
- abrir la carpeta local de preferencias de Cadmus.

## Como usar

1. Abra `Cadmus > Configuracoes Cadmus`.
2. En **General**:
   - Defina la carpeta de proyectos (opcional).
   - Elija el SRC predeterminado (recomendado: EPSG:4326 WGS84).
   - Elija el idioma de la interfaz o `Auto-detectar`.
   - Ajuste la precision de campos vectoriales (0 a 10 decimales).
   - Ajuste el umbral asincrono (1 a 100000000 entidades).
   - Marque/desmarque las categorias visibles en la barra de herramientas.
3. En **Calculos Vectoriales**:
   - Elija el metodo de calculo: `Elipsoidal`, `Cartesiano` o `Ambos`.
   - Defina los sufijos de los campos de area (cartesianos y elipsoidales).
4. Haga clic en `Save`.

## Lo que el plugin hace realmente

- Carga las preferencias guardadas con `load_tool_prefs()`.
- Guarda la configuracion en **tres** claves de preferencias:
  - clave `SYSTEM` (preferencias globales de la aplicacion);
  - clave `VECTOR_FIELDS` (sufijos de area);
  - clave `settings` (estado de la ventana y secciones plegables).
- Valida que los sufijos cartesiano y elipsoidal no sean iguales; si lo son, cancela el guardado y muestra una advertencia.
- Muestra un mensaje de confirmacion despues de guardar.
- Recarga las cadenas de traduccion con el nuevo idioma seleccionado.
- Cierra la ventana justo despues de aplicar las preferencias.
- Permite abrir la carpeta local donde se almacenan los archivos de preferencias.
- Si cambia la visibilidad de las categorias de la barra de herramientas, emite una senal para actualizar la barra dinamicamente.

## Significado de cada opcion

- `Carpeta de proyectos`: guarda la ruta en `projects_folder`.
- `SRC por defecto`: guarda el authid (ej: `EPSG:4326`) en `default_crs_authid`.
- `Idioma`: guarda la locale (ej: `pt_BR`) en `plugin_language`; si es `Auto-detectar`, elimina la clave para que QGIS decida.
- `Metodo de calculo vectorial`: guarda el texto en `calculation_method`.
- `Sufijo cartesiano`: guarda en `cartesian_suffix` (clave `VECTOR_FIELDS`).
- `Sufijo elipsoidal`: guarda en `ellipsoidal_suffix` (clave `VECTOR_FIELDS`).
- `Precision de campos vectoriales`: guarda un valor entero en `vector_field_precision`.
- `Umbral asincrono`: guarda un valor entero en `async_threshold_features`.
- `Barra de herramientas - Categorias visibles`: guarda un diccionario de categorias en `toolbar_category_visibility`.

## Metodo de calculo vectorial (Elipsoidal vs Cartesiano)

### Elipsoidal (recomendado para WGS84 / SRC geografico)

Calcula areas y longitudes sobre la **superficie curva del elipsoide** de la Tierra (ej: WGS84).
- **Ideal para capas en SRC geografico (lat/lon)** como WGS84 (EPSG:4326).
- Los resultados estan en **metros / metros²**, independientemente del SRC de la capa.
- Es mas preciso para grandes areas y altas latitudes, pues considera la curvatura terrestre.
- **Ejemplo**: un area calculada en EPSG:4326 con este metodo devuelve valores fisicos reales en m².

### Cartesiano (recomendado para UTM / SRC proyectado)

Calcula areas y longitudes en el **plano cartesiano** del SRC de la capa.
- **Ideal para SRC proyectados como UTM** (ej: EPSG:31983 SIRGAS 2000 / UTM 23S), donde las unidades ya estan en metros.
- Es rapido y simple, pues usa solo calculos planares (teorema de Pitagoras / producto vectorial).
- **Precaucion**: en SRC geografico (grados), el calculo cartesiano produciria valores en **grados / grados²**, sin significado fisico.
- Si se solicita el modo Cartesiano en una capa geografica, el plugin cambia automaticamente a `Ambos` y muestra una advertencia.

### Ambos

Calcula los dos metodos simultaneamente.
- Genera **dos campos separados** para cada metrica (uno cartesiano y uno elipsoidal).
- Usa los sufijos configurados abajo para diferenciar los campos.
- Util para comparar resultados y validar la calidad de los datos.

## Tooltips (descripciones de los widgets)

Al pasar el mouse sobre cualquier campo de la configuracion, se muestra una descripcion detallada:

- **Carpeta de proyectos**: carpeta raiz donde se crean y organizan los proyectos de Cadmus; se usa como ubicacion predeterminada para nuevos proyectos y archivos de entrada/salida.
- **SRC por defecto**: sistema de referencia usado cuando no se especifica ningun SRC; WGS84 (EPSG:4326) es el predeterminado recomendado para datos globales.
- **Idioma**: define el idioma de la interfaz; `Auto-detectar` usa el idioma de QGIS.
- **Precision de campos vectoriales**: numero de decimales usados en area, longitud y coordenadas X/Y; valores mayores aumentan la precision pero generan campos mas largos.
- **Umbral asincrono**: numero minimo de entidades para que el procesamiento se ejecute en segundo plano; las capas mas pequenas que el umbral se ejecutan de forma sincrona (bloqueante).
- **Barra de herramientas - Categorias visibles**: controla que categorias de herramientas aparecen en la barra; desmarque para ocultar botones.
- **Metodo de calculo**: elipsoidal (ideal WGS84/geografico), cartesiano (ideal UTM/proyectado) o ambos.
- **Sufijo cartesiano**: texto anadido a los campos calculados en modo cartesiano; vacio = sin sufijo.
- **Sufijo elipsoidal**: texto anadido a los campos calculados en modo elipsoidal; predeterminado `_eli` para diferenciar de los cartesianos.

## Comportamiento importante

- El umbral asincrono actual se mide en numero de entidades, no en MB.
- La precision acepta valores entre 0 y 10.
- El umbral asincrono acepta valores entre 1 y 100000000.
- El codigo aun lee la antigua clave `async_threshold_bytes` por compatibilidad, pero ahora usa el limite por entidades.
- Los sufijos cartesiano y elipsoidal no pueden ser iguales; el guardado se bloquea con una advertencia.
- Este plugin solo guarda preferencias; no ejecuta calculos vectoriales por si mismo.

## Carpeta de preferencias

- El enlace de la interfaz intenta abrir `PREF_FOLDER` en el sistema operativo.
- Si la carpeta no existe, el plugin muestra una advertencia en lugar de abrir el explorador de archivos.

## Cuando usarla

Use esta herramienta cuando quiera ajustar el comportamiento predeterminado de otras herramientas de Cadmus que dependen de estas preferencias globales.

## Cuidados

- Cambie el metodo de calculo solo si tiene sentido para su flujo de trabajo.
- Si reduce demasiado el umbral asincrono, mas operaciones pueden pasar a ejecutarse en segundo plano.
- Si nota un comportamiento extrano despues de cambiar preferencias, revise los archivos guardados en la carpeta de preferencias.