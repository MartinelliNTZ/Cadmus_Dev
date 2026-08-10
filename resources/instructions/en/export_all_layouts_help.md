<!--
Versao: 1.0.0
Data de criacao: 2026-08-07
Data da ultima modificacao: 2026-08-10
-->

# Export All Layouts — Quick Guide

Exports all layouts from the current project to PDF, PNG and/or SVG, with georeferencing, output DPI, final file merging and individual layout selection options.

## Output formats

Select at least one format:

- `Export PDF` — generates one PDF per layout. With `Georeference PDF` checked, the PDF receives georeferencing.
- `Export PNG` — generates a PNG image per layout.
- `Export SVG` — generates a vector SVG per layout.

Export is blocked if no format is selected.

## General options

- `Output DPI` — defines the resolution of the exported files. Value `0` (default) uses the DPI set in the layout. Higher values apply a fixed DPI to PDFs, PNGs and SVGs.
- `Max Width` — maximum width in pixels used when PNGs are merged into a final PDF.
- `Output folder` — destination folder for the files. The default is `exports` inside the project directory, created automatically if it does not exist.

## Layout selection

- Click `Layouts` to choose which layouts to export.
- The selection is saved for the next tool runs.
- If no layout is selected, all project layouts are exported.
- If the project has no layouts, the tool shows a warning.

## File merging

- `Merge PDF` — merges all exported PDFs into a single `_PDF_UNICO_FINAL.pdf`.
- `Merge PNG` — converts all exported PNGs into a single `_PNG_MERGED_FINAL.pdf`, respecting `Max Width`.

Merging depends on optional libraries: `PyPDF2` (PDFs) and `Pillow` (PNGs). If the library is missing, the tool asks whether to install it; declining skips the merge and the export continues normally.

## File names

- Invalid filesystem characters (`< > : " / \ | ? *`) are removed from each layout name.
- With `Replace Existing` unchecked (default), files with an existing name get a numeric suffix (`Layout_1`, `Layout_2`...).
- With `Replace Existing` checked, existing files are overwritten without creating numbered copies.

## How to use

1. Open `Cadmus > Export All Layouts`.
2. Select at least one format: PDF, PNG and/or SVG.
3. Adjust `DPI`, `Georeference PDF`, `Max Width` and merges as needed.
4. Choose the output folder (default `.../exports`).
5. Optional: click `Layouts` and select the desired layouts.
6. Click `Export` and follow the progress bar (you can cancel).
7. At the end, a summary shows successes, errors and the destination folder; merged files are indicated.

## What the plugin actually does

- Reads project layouts via `layoutManager().layouts()` and filters by the selection made in `Layouts`.
- Validates that at least one format is selected before starting.
- Creates the output folder automatically if it does not exist.
- Exports each layout with `QgsLayoutExporter` in the selected formats, applying `dpi` when greater than zero.
- Applies georeferencing only to the PDF when `Georeference PDF` is checked.
- Generates unique names with a numeric suffix when `Replace Existing` is unchecked.
- Counts a layout as successful if at least one format was exported successfully.
- Shows a `ProgressDialog`, supports cancel and stops the loop at the current point.
- At the end, runs the requested merges (`_PDF_UNICO_FINAL.pdf` and/or `_PNG_MERGED_FINAL.pdf`).
- Automatically saves preferences (formats, DPI, Max Width, folder, selected layouts) when the window closes.

## Important behavior

- At least one format (PDF, PNG or SVG) must be selected.
- If a layout fails in one format but succeeds in another, it is counted as a success and the error appears in the summary.
- Canceling the export keeps the already exported files in the folder.
- `DPI` with value 0 delegates to the layout; positive values override the DPI of the generated files.

## When to use it

Use this tool when you need to quickly export all layouts from a project without opening and saving them one by one.

It is especially useful for:

- delivering a complete sheet set;
- generating batch revisions;
- consolidating PDF or PNG output into a single final file;
- generating vector (SVG) versions of the layouts.

## Notes

- Review the output folder before running, especially if `Replace Existing` is checked.
- Check the generated files when layouts have similar names.
- For large projects, export first without merging to validate the result.
- `Merge PNG` can produce large PDFs depending on the number of images and the `Max Width` set.