<!--
Versao: 1.0.0
Data de criacao: 2026-08-07
Data da ultima modificacao: 2026-08-10
-->

# Exportar Todos los Layouts — Guia Rapida

Exporta todos los layouts del proyecto actual a PDF, PNG y/o SVG, con opciones de georreferenciacion, DPI de salida, union de archivos finales y seleccion individual de layouts.

## Formatos de salida

Seleccione al menos un formato:

- `Export PDF` — genera un PDF por layout. Con `Georeference PDF` marcado, el PDF recibe georreferenciacion.
- `Export PNG` — genera una imagen PNG por layout.
- `Export SVG` — genera un SVG vectorial por layout.

La exportacion se bloquea si no se marca ningun formato.

## Opciones generales

- `DPI de salida` — define la resolucion de los archivos exportados. El valor `0` (predeterminado) usa el DPI configurado en el layout. Los valores mayores aplican un DPI fijo a los PDF, PNG y SVG.
- `Max Width` — ancho maximo en pixeles usado cuando los PNG se unen en un PDF final.
- `Carpeta de salida` — ubicacion de destino de los archivos. El valor predeterminado es `exports` dentro del directorio del proyecto, creada automaticamente si no existe.

## Seleccion de layouts

- Haga clic en `Layouts` para elegir que layouts exportar.
- La seleccion se guarda para las proximas ejecuciones de la herramienta.
- Si no se selecciona ningun layout, se exportan todos los layouts del proyecto.
- Si el proyecto no tiene layouts, la herramienta muestra un aviso.

## Union de archivos

- `Merge PDF` — une todos los PDF exportados en un unico `_PDF_UNICO_FINAL.pdf`.
- `Merge PNG` — convierte todos los PNG exportados en un unico `_PNG_MERGED_FINAL.pdf`, respetando el `Max Width`.

Las uniones dependen de bibliotecas opcionales: `PyPDF2` (PDF) y `Pillow` (PNG). Si falta la biblioteca, la herramienta pregunta si desea instalarla; si se rechaza, la union se ignora y la exportacion continua normalmente.

## Nombres de archivo

- Los caracteres invalidos para el sistema de archivos (`< > : " / \ | ? *`) se eliminan del nombre de cada layout.
- Con `Replace Existing` desmarcado (predeterminado), los archivos con nombre ya existente reciben un sufijo numerico (`Layout_1`, `Layout_2`...).
- Con `Replace Existing` marcado, los archivos existentes se sobrescriben sin crear copias numeradas.

## Como usar

1. Abra `Cadmus > Export All Layouts`.
2. Marque al menos un formato: PDF, PNG y/o SVG.
3. Ajuste `DPI`, `Georeference PDF`, `Max Width` y las uniones segun sea necesario.
4. Elija la carpeta de salida (predeterminada `.../exports`).
5. Opcional: haga clic en `Layouts` y seleccione los layouts deseados.
6. Haga clic en `Export` y siga la barra de progreso (es posible cancelar).
7. Al final, un resumen muestra exitos, errores y carpeta de destino; los archivos unidos se indican.

## Lo que el plugin hace realmente

- Lee los layouts del proyecto via `layoutManager().layouts()` y filtra por la seleccion hecha en `Layouts`.
- Valida que al menos un formato este marcado antes de iniciar.
- Crea la carpeta de salida automaticamente si no existe.
- Exporta cada layout con `QgsLayoutExporter` en los formatos marcados, aplicando `dpi` cuando es mayor que cero.
- Aplica georreferenciacion solo al PDF cuando `Georeference PDF` esta marcado.
- Genera nombres unicos con sufijo numerico cuando `Replace Existing` esta desmarcado.
- Cuenta un layout como exitoso si al menos un formato se exporto correctamente.
- Muestra un `ProgressDialog`, permite cancelar y detiene el bucle en el punto actual.
- Al final, ejecuta las uniones solicitadas (`_PDF_UNICO_FINAL.pdf` y/o `_PNG_MERGED_FINAL.pdf`).
- Guarda automaticamente las preferencias (formatos, DPI, Max Width, carpeta, layouts seleccionados) al cerrar la ventana.

## Comportamiento importante

- Debe marcarse al menos un formato (PDF, PNG o SVG).
- Si un layout falla en un formato pero funciona en otro, se cuenta como exitoso y el error aparece en el resumen.
- Cancelar la exportacion mantiene los archivos ya exportados en la carpeta.
- El `DPI` con valor 0 delega al layout; los valores positivos sobrescriben el DPI de los archivos generados.

## Cuando usarla

Use esta herramienta cuando necesite exportar rapidamente todos los layouts de un proyecto sin abrirlos y guardarlos uno por uno.

Es especialmente util para:

- entregar un conjunto completo de planos;
- generar revisiones en lote;
- consolidar la salida PDF o PNG en un unico archivo final;
- generar versiones vectoriales (SVG) de los layouts.

## Cuidados

- Revise la carpeta de salida antes de ejecutar, sobre todo si `Replace Existing` esta marcado.
- Revise los archivos generados cuando haya layouts con nombres parecidos.
- Para proyectos grandes, exporte primero sin union para validar el resultado.
- `Merge PNG` puede generar PDF grandes segun el numero de imagenes y el `Max Width` definido.