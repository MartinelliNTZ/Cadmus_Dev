# Configuraciones de Cadmus — Guia Rapida

Esta herramienta centraliza preferencias globales usadas por partes del plugin Cadmus.

En el estado actual del codigo, permite:

- elegir el metodo predeterminado de calculo vectorial;
- definir la precision numerica de campos vectoriales;
- definir el umbral de entidades para procesamiento asincrono;
- abrir la carpeta local de preferencias de Cadmus.

## Como usar

1. Abra `Cadmus > Configuracoes Cadmus`.
2. Elija el metodo de calculo vectorial:
- `Elipsoidal`
- `Cartesiano`
- `Ambos`
3. Ajuste la precision de campos vectoriales.
4. Ajuste el umbral asincrono.
5. Haga clic en `Save`.

## Lo que el plugin hace realmente

- Carga las preferencias guardadas con `load_tool_prefs()`.
- Guarda la configuracion bajo la clave de preferencias `settings`.
- Muestra un mensaje de confirmacion despues de guardar.
- Cierra la ventana justo despues de aplicar las preferencias.
- Permite abrir la carpeta local donde se almacenan los archivos de preferencias.

## Significado de cada opcion

- `Metodo de calculo vectorial`: define el texto almacenado en `calculation_method`.
- `Precision de campos vectoriales`: guarda un valor entero en `vector_field_precision`.
- `Umbral asincrono`: guarda un valor entero en `async_threshold_features`.

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
