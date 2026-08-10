<!--
Versao: 1.0.0
Data de criacao: 2026-08-10
Data da ultima modificacao: 2026-08-10
-->

# Path Extension — Quick Guide

Tool to remove/restore file extensions or zip/unzip photos in paths stored in features of a vector layer.

File paths are read from a layer field and the result of each operation is written to the `NewPath` field (created automatically).

## Operation modes

- `Remove Extension` — removes the dot and the extension from the physical path. Example: `C:/fotos/foto.jpg` becomes `C:/fotos/fotojpg`. The file on disk is renamed.
- `Restore Extension` — restores the dot and the extension. Example: the file `C:/fotos/fotojpg` on disk becomes `C:/fotos/foto.jpg` again.
- `Zip` — groups features from the same folder and creates ONE ZIP file per folder containing the files pointed by the features. Removes the original files after compression.
- `Unzip` — groups features from the same folder, extracts the folder ZIP and removes the ZIP after extraction.

## How to use

1. Open `Cadmus > Path Extension`.
2. Select the input vector layer (or a vector file, if you prefer).
3. Optional: check `Only selected features` to process only the current selection.
4. Select the field that contains the file paths. If the layer has a field named `path`, it is auto-selected.
5. Choose the operation mode: Remove, Restore, Zip or Unzip.
6. Click `Run`.
7. At the end, a success message is shown in the message bar with the number of changed features.

## What the plugin actually does

- Reads the layer from the UI and the chosen path field.
- Validates that the layer is vector, that an attribute was selected and that a mode was chosen.
- Runs an async pipeline (`AsyncPipelineEngine` with `PathExtensionStep`).
- The task processes the physical files on disk without touching the layer:
  - `remove` and `restore` process feature by feature via `ExplorerUtils`.
  - `zip` and `unzip` group features by folder and delegate to `FileCompressUtils`.
- The step adds the `NewPath` (text) field to the layer, if it does not exist yet.
- On finish, the step writes the resulting new path into the `NewPath` field of each feature (main thread) and repaints the layer.
- Shows in the message bar: `Processing finished: N features changed`.
- Saves the last used mode in the tool preferences.

## Important behavior

- `NewPath` is created in the layer and receives the new path of each processed feature; skipped or errored features are not changed.
- `Zip` mode: the ZIP is created with the folder name (e.g. `C:/fotos/fotos.zip`) and contains only the files pointed by the features — not all files in the folder.
- `Unzip` mode: the folder ZIP is extracted into the directory itself and the ZIP file is removed afterwards.
- If a path is empty or invalid, the feature is counted as an error.
- Missing file or denied permission generate a counted error, but processing continues on the remaining features.
- Processing is async and the UI does not freeze; the task can be canceled during execution.

## When to use it

Use this tool when you want to:

- normalize photo paths by removing or restoring the extension in batch;
- compress into ZIP the files referenced by the features of a layer;
- extract ZIPs referenced by the features, restoring the original files.

## Notes

- `Zip` mode removes the original files after creating the ZIP — make a backup if needed.
- `Unzip` mode removes the ZIP after extraction.
- Check that the selected field really contains valid absolute paths.
- Use `Only selected features` to test on a small set before processing the whole layer.
- Processing changes files on disk; review the folder before running.