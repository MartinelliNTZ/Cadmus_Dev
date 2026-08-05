# Cadmus Settings — Quick Guide

This tool centralizes global preferences used by parts of the Cadmus plugin.

In the current code, it lets you:

- choose the default vector calculation method;
- define numeric precision for vector fields;
- define the feature threshold for asynchronous processing;
- open the local Cadmus preferences folder.

## How to use

1. Open `Cadmus > Configuracoes Cadmus`.
2. Choose the vector calculation method:
- `Ellipsoidal`
- `Cartesian`
- `Both`
3. Adjust the vector field precision.
4. Adjust the asynchronous threshold.
5. Click `Save`.

## What the plugin actually does

- Loads saved preferences with `load_tool_prefs()`.
- Saves the settings under the `settings` preference key.
- Shows a confirmation message after saving.
- Closes the window right after applying the preferences.
- Lets you open the local folder where preference files are stored.

## What each option means

- `Vector calculation method`: defines the text stored in `calculation_method`.
- `Vector fields precision`: stores an integer value in `vector_field_precision`.
- `Async threshold`: stores an integer value in `async_threshold_features`.

## Vector calculation method (Ellipsoidal vs Cartesian)

### Ellipsoidal (recommended for WGS84 / geographic CRS)

Calculates areas and lengths over the **curved surface of the Earth's ellipsoid** (e.g., WGS84).
- **Ideal for layers in geographic CRS (lat/lon)** such as WGS84 (EPSG:4326).
- Results are in **meters / meters²**, regardless of the layer CRS.
- More accurate for large areas and high latitudes, as it considers the Earth's curvature.
- **Example**: an area calculated in EPSG:4326 with this method returns real physical values in m².

### Cartesian (recommended for UTM / projected CRS)

Calculates areas and lengths in the **cartesian plane** of the layer CRS.
- **Ideal for projected CRS such as UTM** (e.g., EPSG:31983 SIRGAS 2000 / UTM 23S), where units are already meters.
- Fast and simple, using only planar calculations (Pythagorean theorem / cross product).
- **Caution**: in geographic CRS (degrees), cartesian calculation would produce values in **degrees / degrees²**, without physical meaning.
- If Cartesian mode is requested on a geographic layer, the plugin automatically switches to `Both` and shows a warning.

### Both

Calculates both methods simultaneously.
- Generates **two separate fields** for each metric (one cartesian and one ellipsoidal).
- Uses the suffixes configured below to differentiate the fields.
- Useful for comparing results and validating data quality.

## Tooltips (widget descriptions)

Hovering over any settings field shows a detailed description:

- **Projects folder**: root folder where Cadmus projects are created and organized; used as the default location for new projects and input/output files.
- **Default CRS**: reference system used when no CRS is specified; WGS84 (EPSG:4326) is the recommended default for global data.
- **Language**: defines the interface language; `Auto-detect` uses the QGIS language.
- **Vector fields precision**: number of decimal places used in area, length, and X/Y coordinates; higher values increase precision but generate longer fields.
- **Async threshold**: minimum number of features for processing to run in the background; layers smaller than the threshold run synchronously (blocking).
- **Toolbar - Visible categories**: controls which tool categories appear on the toolbar; uncheck to hide buttons.
- **Calculation method**: ellipsoidal (ideal WGS84/geographic), cartesian (ideal UTM/projected), or both.
- **Cartesian suffix**: text added to fields calculated in cartesian mode; empty = no suffix.
- **Ellipsoidal suffix**: text added to fields calculated in ellipsoidal mode; default `_eli` to differentiate from cartesian fields.

## Important behavior

- The current asynchronous threshold is measured in number of features, not in MB.
- Precision accepts values from 0 to 10.
- The asynchronous threshold accepts values from 1 to 100000000.
- The code still reads the old `async_threshold_bytes` key for backward compatibility, but now uses the feature-based limit.
- This plugin only saves preferences; it does not run vector calculations by itself.

## Preferences folder

- The interface link tries to open `PREF_FOLDER` in the operating system.
- If the folder does not exist, the plugin shows a warning instead of opening the file explorer.

## When to use it

Use this tool when you want to adjust the default behavior of other Cadmus tools that depend on these global preferences.

## Notes

- Change the calculation method only if it fits your workflow.
- If you lower the asynchronous threshold too much, more operations may run in the background.
- If behavior becomes unexpected after changing preferences, review the files stored in the preferences folder.
