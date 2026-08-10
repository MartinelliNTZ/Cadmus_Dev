<!--
Versao: 1.0.0
Data de criacao: 2026-08-10
Data da ultima modificacao: 2026-08-10
-->

# Extension de Path — Guia Rapida

Herramienta para eliminar/restaurar la extension de archivos o comprimir/descomprimir fotos en los paths almacenados en las entidades de una capa vectorial.

Las rutas de los archivos se leen de un campo de la capa y el resultado de cada operacion se escribe en el campo `NewPath` (creado automaticamente).

## Modos de operacion

- `Eliminar Extension` — elimina el punto y la extension del path fisico. Ejemplo: `C:/fotos/foto.jpg` pasa a ser `C:/fotos/fotojpg`. El archivo en disco se renombra.
- `Restaurar Extension` — restaura el punto y la extension. Ejemplo: el archivo `C:/fotos/fotojpg` en disco vuelve a ser `C:/fotos/foto.jpg`.
- `Comprimir (ZIP)` — agrupa las entidades de la misma carpeta y crea UN archivo ZIP por carpeta con los archivos apuntados por las entidades. Elimina los archivos originales tras la compresion.
- `Descomprimir (UNZIP)` — agrupa las entidades de la misma carpeta, extrae el ZIP de la carpeta y elimina el ZIP tras la extraccion.

## Como usar

1. Abra `Cadmus > Extension de Path`.
2. Seleccione la capa vectorial de entrada (o un archivo vectorial, si lo prefiere).
3. Opcional: marque `Solo entidades seleccionadas` para procesar unicamente la seleccion actual.
4. Seleccione el campo que contiene las rutas de los archivos. Si la capa tiene un campo llamado `path`, se auto-selecciona.
5. Elija el modo de operacion: Eliminar, Restaurar, Comprimir o Descomprimir.
6. Haga clic en `Ejecutar`.
7. Al final, se muestra un mensaje de exito en la barra de mensajes con la cantidad de entidades modificadas.

## Lo que el plugin hace realmente

- Lee la capa de la interfaz y el campo de path elegido.
- Valida que la capa sea vectorial, que se haya seleccionado un atributo y que se haya elegido un modo.
- Ejecuta una pipeline asincrona (`AsyncPipelineEngine` con `PathExtensionStep`).
- La task procesa los archivos fisicos en disco sin tocar la capa:
  - `remove` y `restore` procesan entidad por entidad via `ExplorerUtils`.
  - `zip` y `unzip` agrupan las entidades por carpeta y delegan en `FileCompressUtils`.
- El step agrega el campo `NewPath` (texto) a la capa, si aun no existe.
- Al finalizar, el step escribe en el campo `NewPath` de cada entidad la nueva ruta resultante (hilo principal) y repinta la capa.
- Muestra en la barra de mensajes: `Procesamiento concluido: N entidades modificadas`.
- Guarda el ultimo modo usado en las preferencias de la herramienta.

## Comportamiento importante

- `NewPath` se crea en la capa y recibe la nueva ruta de cada entidad procesada; las entidades omitidas o con error no se modifican.
- Modo `Comprimir`: el ZIP se crea con el nombre de la carpeta (ej: `C:/fotos/fotos.zip`) y contiene solo los archivos apuntados por las entidades — no todos los archivos de la carpeta.
- Modo `Descomprimir`: el ZIP de la carpeta se extrae en el propio directorio y el archivo ZIP se elimina a continuacion.
- Si una ruta esta vacia o es invalida, la entidad se contabiliza como error.
- Archivo inexistente o permiso denegado generan un error contabilizado, pero el procesamiento continua con las demas entidades.
- El procesamiento es asincrono y la interfaz no se congela; es posible cancelar la task durante la ejecucion.

## Cuando usarla

Use esta herramienta cuando quiera:

- normalizar rutas de fotos eliminando o restaurando la extension en lote;
- comprimir en ZIP los archivos referenciados por las entidades de una capa;
- extraer ZIPs referenciados por las entidades, restaurando los archivos originales.

## Cuidados

- El modo `Comprimir` elimina los archivos originales tras crear el ZIP — haga una copia de seguridad si es necesario.
- El modo `Descomprimir` elimina el ZIP tras la extraccion.
- Compruebe que el campo seleccionado realmente contiene rutas absolutas validas.
- Use `Solo entidades seleccionadas` para probar en un conjunto pequeno antes de procesar toda la capa.
- El procesamiento modifica archivos en disco; revise la carpeta antes de ejecutar.