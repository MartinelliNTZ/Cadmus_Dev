# -*- coding: utf-8 -*-
from .Strings_pt_BR import Strings_pt_BR


class Strings_en(Strings_pt_BR):
    """Strings for English (en)"""

    # General
    APP_NAME = "Cadmus"
    PLUGIN_LANGUAGE = "Plugin Language"

    # About
    ABOUT_CADMUS = "About Cadmus"
    VERSION = "Version"
    UPDATED_ON = "Last updated"
    CREATED_ON = "Created on"
    CREATOR = "Author"
    LOCATION = "Location"

    # Buttons
    CLOSE = "Close"
    SAVE = "Save"
    LOAD_FILES = "Load Files"
    EXPORT = "Export"
    CANCEL = "Cancel"
    EXECUTE = "Run"
    COPIED = "Copied"
    COPY = "Copy"
    SELECT = "Select"
    REMOVE = "Remove"
    INVERT = "Invert"
    ENABLE = "Enable"
    INFO = "Info"
    INSTRUCTIONS = "Instructions"
    AUTO_DETECT = "Auto-detect"

    # Common labels
    MENU_SYSTEM = "System"
    MENU_LAYOUTS = "Layouts"
    MENU_FOLDER = "Folder"
    MENU_VECTOR = "Vector"
    MENU_AGRICULTURE = "Agriculture"
    MENU_RASTER = "Raster"
    OPTIONS = "Options"
    SAVING = "Saving"
    STYLES = "Styles"
    WARNING = "Warning"
    ERROR = "Error"
    ADVANCED_PARAMETERS = "Advanced Parameters"
    APP_PREFERENCES = "Application Preferences"
    OPEN_PREFERENCES_FOLDER = "Open Preferences Folder"
    FILE_TYPES = "File Types"
    ROOT_FOLDER = "Root folder:"
    OUTPUT_FOLDER = "Output folder:"
    INPUT_LINE_LAYER = "Line Layer (INPUT):"
    SOURCE_LAYER = "Source Layer:"
    TARGET_LAYER = "Target Layer:"
    IMPLEMENT_SIZE = "Implement width (meters):"
    VECTOR_CALCULATION_METHOD = "Vector Calculation Method"
    VECTOR_FIELDS_PRECISION = "Vector field precision (decimal places):"
    ASYNC_THRESHOLD = "Async threshold (feature count):"
    CALCULATION_METHOD_LABEL = "Vector calculation method:"
    SEARCH_TEXT = "Text to search:"
    REPLACE_WITH_NEW_TEXT = "Replace with:"
    SOURCE_LAYER_ATTRIBUTES = "Source layer attributes"
    ATTRIBUTES = "Attributes"
    USE_ALL_ATTRIBUTES = "Use all attributes"
    EXPORT_OPTIONS = "Export Options"
    MAX_WIDTH_PNG = "Max PNG width (px):"
    USE_PROJECT_FOLDER = "Use project folder"
    EXPORT_PDF = "Export as PDF"
    EXPORT_PNG = "Export as PNG"
    MERGE_PDFS_FINAL = "Merge PDFs into final file"
    MERGE_PNGS_FINAL = "Convert PNGs into PDF"
    REPLACE_EXISTING_FILES = "Overwrite existing files"
    WGS84_EPSG4326 = "WGS 84 (EPSG:4326)"
    UTM_SIRGAS_2000 = "UTM SIRGAS 2000"
    ALTIMETRY_OPENTOPO = "Elevation (OpenTopoData)"
    APPROX_ALTITUDE_METERS = "Approx. elevation (m)"
    LATITUDE_DECIMAL = "Latitude (Decimal)"
    LONGITUDE_DECIMAL = "Longitude (Decimal)"
    LATITUDE_DMS = "Latitude (DMS)"
    LONGITUDE_DMS = "Longitude (DMS)"
    EASTING_X = "Easting (X)"
    NORTHING_Y = "Northing (Y)"
    ADDRESS_OSM = "Address (OSM):"
    COPY_WGS84_FULL = "Copy WGS84 (Full)"
    COPY_UTM_FULL = "Copy UTM (Full)"
    COPY_LOCATION_FULL = "Copy Location (Full)"
    POINT_COORDINATES = "Point Coordinates"
    ZONE = "Zone"
    HEMISPHERE = "Hemisphere"
    CITY = "City"
    FILE_NOT_FOUND = "File not found"
    INTERMEDIATE_REGION = "Intermediate Region"
    STATE = "State"
    REGION = "Region"
    COUNTRY = "Country"
    LOADING = "Loading..."
    LOADING_LOWER = "loading..."
    UNAVAILABLE = "Unavailable"
    NO_PATH_SELECTED = "No path selected"
    FILES_SELECTED = "file(s) selected"
    ITEMS_SELECTED = "item(s)"
    ONLY_SELECTED_FEATURES = "Selected features only"
    APPLY_QML_STYLE = "Apply QML style"
    QML_LABEL = "QML:"
    SAVE_TO_FILE = "Save to file:"
    SELECT_PATH = "Select Path"
    BUTTON = "Button"
    SAVE_FILE = "Save file"
    SELECT_FILE = "Select file"
    POINTS = "Points"
    TRACK = "Track"

    # Common option labels
    CASE_SENSITIVE = "Case sensitive"
    FULL_LABEL_REPLACE = "Replace entire label when match is found"
    LOAD_ONLY_MISSING_FILES = "Load only files not already added to the project"
    PRESERVE_FOLDER_STRUCTURE = "Group layers based on folder/subfolder structure"
    DO_NOT_GROUP_LAST_FOLDER = "Do not group last folder level"
    CREATE_PROJECT_BACKUP_IF_SAVED = (
        "Create project backup before loading (if already saved)"
    )

    # Common messages
    SUCCESS_MESSAGE = "Processing completed successfully."
    ERROR_LAYER_NOT_FOUND = "Error: Layer not found."
    SELECT_VALID_FOLDER = "Please select a valid folder."
    SELECT_AT_LEAST_ONE_FILE_TYPE = "Select at least one file type."
    SELECT_AT_LEAST_ONE_EXPORT_FORMAT = "Select at least one format (PDF or PNG)"
    SELECT_VALID_LINE_LAYER = "Select a valid line layer."
    INVALID_SOURCE_LAYER = "Invalid source layer"
    INVALID_TARGET_LAYER = "Invalid target layer"
    INVALID_INPUT_LAYER = "Invalid input layer."
    FINAL_LAYER_NOT_FOUND = "Error: final layer not found in context."
    BUFFER_CANNOT_BE_ZERO = "Buffer cannot be zero"
    ASYNC_STARTED = "Background execution started. Check logs for progress."
    ASYNC_START_ERROR = "Error starting async execution:"
    ASYNC_FINISHED = "Async execution completed."
    ASYNC_EXECUTION_ERROR = "Error during async execution:"
    FILES_LOADED_PREFIX = "Loaded"
    FILES_SUFFIX = "files."
    SETTINGS_SAVED_TITLE = "Settings Saved"
    SETTINGS_SAVED_MESSAGE = "Settings saved successfully."
    PREFERENCES_FOLDER_NOT_FOUND = "Preferences folder not found:"
    ENTER_TEXT_TO_SEARCH = "Enter text to search."
    CONFIRM_REPLACEMENTS = "Confirm replacements"
    SEARCH_LABEL = "Search:"
    REPLACE_WITH_LABEL = "Replace with:"
    DESTRUCTIVE_OPERATION_WARNING = "Warning - destructive operation"
    LAYOUTS_ANALYZED = "Layouts analyzed:"
    CHANGES_APPLIED = "Replacements applied:"
    REPLACEMENT_COMPLETED_TITLE = "Replacement completed"
    PROJECT_BACKUP_INFO = "Backup: a copy of the project (.qgz) will be created in a backup folder next to the project file."
    LAYER_MUST_BE_EDITABLE = "Layer must be in edit mode"
    NO_ATTRIBUTE_SELECTED = "No attribute selected"
    ATTRIBUTES_COPIED_SUCCESS = "Attributes copied successfully (changes not saved)"
    REQUIRED_LIBRARY = "Required library"
    PYPDF2_REQUIRED_MESSAGE = "To merge PDFs, the PyPDF2 package is required.\n\nWould you like to install it now?"
    PILLOW_REQUIRED_MESSAGE = "To convert PNGs into PDF, the Pillow package is required.\n\nWould you like to install it now?"
    EXPORTING_LAYOUTS = "Exporting layouts..."
    FAILED_EXPORT_PDF = "Failed to export PDF:"
    FAILED_EXPORT_PNG = "Failed to export PNG:"
    ERROR_EXPORTING = "Error during export"
    FAILED_MERGE_PDFS = "Failed to merge PDFs:"
    FAILED_MERGE_PNGS = "Failed to merge PNGs:"
    ERRORS_FOUND = "Errors found:"
    LAYOUTS_EXPORTED_SUCCESS = "Layout(s) exported successfully!"
    PDFS_MERGED = "PDFs merged"
    PNGS_MERGED = "PNGs merged"
    EXPORT_LAYOUTS_COMPLETED = "Layout export completed"
    LOCATION_COPIED_TO_CLIPBOARD = "Location copied to clipboard"
    ADDRESS_COPIED_TO_CLIPBOARD = "Address copied to clipboard"

    SELECT_VECTOR_LAYER = "Select a vector layer"
    SELECT_EDITABLE_VECTOR_LAYER = "Select an editable vector layer"
    LAYER_HAS_NO_FEATURES = "The layer has no features"
    OPERATION_CANCELLED_BY_USER = "Operation cancelled by the user"
    GEOMETRY_TYPE_NOT_SUPPORTED = "Unsupported geometry type"
    ERROR_IN_PREPARATION = "Error during preparation:"
    KML_FILES_ARE_NOT_EDITABLE = "KML files are not editable."
    CONVERT_LAYER_TO_GPKG_OR_SHP_BEFORE_USING = "Convert the layer to GeoPackage (.gpkg) or Shapefile (.shp) before using this tool."
    LAYER_USES_GEOGRAPHIC_CRS = "Layer uses Geographic CRS"
    CARTESIAN_MODE_RESULTS_IN_DEGREES2 = (
        "Cartesian mode would result in values in degrees²."
    )
    CALCULATING_BOTH_MODES_AUTOMATICALLY = "Calculating both modes automatically."
    XY_FIELDS_CALCULATED_SUCCESS = "X/Y fields calculated successfully"
    LINE_LENGTH_CALCULATED_SUCCESS = "Line length calculated successfully"
    POLYGON_AREA_CALCULATED_SUCCESS = "Polygon area calculated successfully"
    ERROR_STARTING_CALCULATION = "Error starting calculation:"
    UNKNOWN_ERROR = "Unknown error"
    CALCULATION_FAILED = "Calculation failed:"
    GEOMETRIES_CONVERTED_TO_MULTIPART_NOT_SAVED = (
        "Geometries converted to multipart (not saved)"
    )
    CONVERT_SELECTED_FEATURES_TO_MULTIPART = (
        "Convert only the selected features to multipart?"
    )
    CONVERT_ALL_FEATURES_TO_MULTIPART = "Convert all features to multipart?"

    # Dependencies
    INSTALLING_DEPENDENCY = "Installing dependency..."
    INSTALLING_DEPENDENCIES = "Installing dependencies"
    DEPENDENCY = "Dependency"
    INSTALLED_SUCCESSFULLY = "installed successfully."
    SUCCESS = "Success"
    INSTALL_DEPENDENCY_FAILED = "Failed to start installation of the library."
    KML_FIELDS_REMOVED_SUCCESS = "KML fields removed successfully"
    NO_KML_FIELDS_FOUND = "No KML fields found to remove"
    ERROR_REMOVING_KML_FIELDS = "Error removing KML fields:"
    RANGE = "Range"
    RASTERS = "Rasters"
    INPUT_POINTS = "Input points"
    REPROJECT_OUTPUT_LAYER_OPTIONAL = "Reproject output layer (optional)"
    SAMPLED_VALUES = "Sampled_Values"
    OPEN_OUTPUT_FOLDER = "Open output folder"
    DISPLAY_HELP_FIELD = "Display help field (must run and restart)"
    OUTPUT_CRS_LABEL = "Output CRS:"
    NONE = "None"
    FILE_SAVED_IN = "File saved in:"
    RASTER_MASS_SAMPLER_TITLE = "Mass Raster Sampling"
    RASTER_WEIGHTED_AVERAGE_TITLE = "Weighted Average of Rasters"
    RASTER_MASS_CLIPPER_TITLE = "Mass Raster Clipping"
    RASTER_MASS_SAMPLER_TOOLTIP = (
        "Runs batch sampling of multiple rasters over a vector layer.\n"
        "Opens the Cadmus provider algorithm in Processing,\n"
        "allowing inputs, fields, and outputs to be configured in the standard interface."
    )
    RASTER_MASS_CLIPPER_TOOLTIP = (
        "Clips multiple rasters in batch using a polygon layer as mask.\n"
        "Opens the Cadmus provider algorithm in Processing,\n"
        "with support for per-feature clipping, correction buffer, and output folder."
    )
    RASTER_DIFFERENCE_STATISTICS_TITLE = "Process Raster Difference"
    VECTOR_TO_SVG_TITLE = "Vector to SVG Converter"
    VECTOR_TO_SVG_TOOLTIP = (
        "Exports a project vector layer to SVG.\n"
        "Lets you configure background, border, and label,\n"
        "and can generate either a single file or one SVG\n"
        "per feature."
    )
    VECTOR_LAYER_LABEL = "Vector Layer"
    BACKGROUND_COLOR = "Background Color"
    BORDER_COLOR = "Border Color"
    BORDER_WIDTH = "Border Width"
    LABEL_COLOR = "Label Color"
    LABEL_SIZE = "Label Size"
    SELECT_FILL_COLOR = "Select fill color"
    SELECT_BORDER_COLOR = "Select border color"
    SELECT_LABEL_COLOR = "Select label color"
    TRANSPARENT_BACKGROUND = "Transparent background"
    SHOW_BORDER = "Show border"
    SHOW_LABEL = "Show label"
    GENERATE_SVG_FOR_EACH_FEATURE = "Generate SVG for each feature"
    SVGS_GENERATED_SUCCESS = "SVG(s) generated successfully."
    INPUT_MASK_POLYGON_LAYER = "Mask layer (polygon)"
    CLIP_PER_EACH_POLYGON = "Clip for each polygon"
    APPLY_CORRECTION_BUFFER_PIXEL_1_1 = "Apply correction buffer (pixel * 1.1)"
    RASTER_FOLDER_OR_SELECT_RASTER_LAYERS = "Raster folder or select raster layers"
    QGIS_RASTER_LAYERS_OR_SELECT_RASTER_FOLDER = (
        "QGIS raster layers or select raster folder"
    )
    OUTPUT_FOLDER_FOR_GENERATED_RASTERS = "Output folder for generated rasters"
    NO_OUTPUT_FOLDER_PROVIDED_USING_TEMP = "No output folder provided. Using temporary:"
    INVALID_FOLDER = "Invalid folder"
    NO_RASTER_FOUND_IN_SPECIFIED_FOLDER = "No raster found in the specified folder."
    INVALID_RASTER_IGNORED = "Invalid raster ignored"
    PROCESSING_RASTER_DIFFERENCE_BY_FOLDER_OR_LAYERS = (
        "Processing raster difference by folder/layers..."
    )
    INFORM_RASTER_FOLDER_OR_SELECT_LAYER = (
        "Provide a raster folder or select at least one raster layer."
    )
    AT_LEAST_2_RASTERS_REQUIRED = (
        "At least 2 rasters are required to calculate differences."
    )
    FOUND_RASTER_COMBINATIONS_FOR_DIFFERENCE = (
        "Raster combinations found for difference:"
    )
    PROCESSING = "Processing"
    NO_OVERLAP_BETWEEN = "No overlap between"
    AND = "and"
    SKIPPING = "Skipping"
    CALCULATION_ERROR_FOR = "Calculation error for"
    DIFFERENCE_RASTER_CREATED = "Difference raster created:"
    STATS_GENERATED_FOR = "Stats generated for"
    FAILED_TO_GENERATE_STATS_FOR = "Failed to generate stats for"
    CONSOLIDATED_REPORT_GENERATED = "Consolidated report generated:"
    DIFFERENCE_STATISTICS_SUMMARY_TITLE = "Raster Difference Statistics Summary"
    TOTAL_PROCESSED_PAIRS = "Total processed pairs:"
    RASTER = "Raster"
    STATISTICS = "Statistics"
    VECTOR = "Vector"
    INTERVAL = "Interval"
    GEOMETRY_LINE_FROM_POINTS_TITLE = "Difference Line Between Points"
    POINT_LAYER_MODE1_FIRST_LAYER_MODE2 = "Point Layer (Mode 1) / First Layer (Mode 2)"
    BASE_ATTRIBUTE_LAYER_A = "Base attribute - layer A"
    USE_SECOND_LAYER_MODE2 = "Use second layer (mode 2)"
    SECOND_POINT_LAYER_MODE2_OPTIONAL = "Second Point Layer (Mode 2 - optional)"
    BASE_ATTRIBUTE_LAYER_B_MODE2 = "Base attribute - layer B (mode 2)"
    DIFFERENCE_LINES = "Difference lines"
    INVALID_LAYER_A = "Invalid layer A."
    MODE2_REQUIRES_SECOND_POINT_LAYER = "Mode 2 requires a second point layer."
    MODE2_INFORM_GROUP_FIELD_LAYER_B = "In mode 2 inform the grouping field of layer B."
    ERROR_CREATING_OUTPUT_LAYER = "Error creating output layer."
    PROCESS_COMPLETED_LINES_GENERATED_SUCCESS = (
        "Process completed: lines generated successfully."
    )
    ATTRIBUTE_STATISTICS_TITLE = "Attribute Statistics"
    INPUT_LAYER = "Input layer"
    EXCLUDE_FIELDS_OPTIONAL = "Fields to exclude (optional)"
    PRECISION_DECIMAL_PLACES = "Precision (decimal places)"
    LOAD_CSV_AUTOMATICALLY_AFTER_EXECUTION = "Load CSV automatically after execution"
    FORCE_CSV_PTBR_FORMAT = "Force CSV in PT-BR format (use ; and ,)"
    CALCULATE = "Calculate"
    OUTPUT_CSV_FILE = "Output CSV file"
    INVALID_LAYER = "Invalid layer."
    NO_NUMERIC_FIELD_FOUND = "No numeric field found."
    FIELD = "Field"
    COUNT = "Count"
    ERROR_SAVING_CSV = "Error saving CSV:"
    FILE_LOADED_AS_LAYER = "File loaded as layer:"
    CSV_FILE_GENERATED = "CSV file generated:"
    MEAN = "Mean"
    MEAN_ABSOLUTE = "Absolute Mean"
    STD_POP = "Std. Deviation (Pop.)"
    STD_SAMPLE = "Std. Deviation (Sample)"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    MEDIAN = "Median"
    PERCENTILE_5 = "Percentile 5%"
    PERCENTILE_95 = "Percentile 95%"
    MODE = "Mode"
    VARIANCE = "Variance"
    SUM = "Sum"
    COEFFICIENT_OF_VARIATION = "Coefficient of Variation"
    SKEWNESS = "Skewness"
    KURTOSIS = "Kurtosis"
    DIFFERENCE_FIELDS_TITLE = "Difference Generator Between Fields"
    POINT_LAYER = "Point Layer"
    BASE_FIELD_SUBTRAHEND = "Base Field (subtrahend)"
    FIELDS_TO_EXCLUDE_FROM_CALCULATION = "Fields to EXCLUDE from calculation"
    PREFIX_FOR_NEW_FIELDS = "Prefix for new fields"
    DIFFERENCE = "Difference"
    NO_EXCLUDED_FIELD_USING_ALL_NUMERIC = (
        "No field excluded -> using all numeric fields."
    )
    BASE = "Base"
    EXCLUDED_FIELDS = "EXCLUDED fields"
    FIELDS_USED_IN_CALCULATION = "Fields used in calculation"
    PREFIX = "Prefix"
    PROCESS_FINISHED_SUCCESS = "Process finished successfully."

    # plugins/DroneCoordinates.py
    DRONE_COORDINATES_TITLE = "DJI Drone Coordinates"
    DRONE_COORDINATES_TOOLTIP = (
        "Reads drone MRK files to generate photo points and flight path.\n"
        "Can match points with image metadata,\n"
        "save results to file, and apply QML styles\n"
        "to both points and generated track."
    )
    RECURSIVE_SEARCH = "Search subfolders"
    PHOTOS_METADATA = "Match with photo metadata"
    PHOTOS_METADATA_REQUIRED_MESSAGE = "To match with photo metadata, the Pillow package is required.\n\nWould you like to install it now?"
    MRK_FOLDER = "MRK folder:"
    SAVE_POINTS_CHECKBOX = "Save MRK points to file?"
    SAVE_IN = "Save to:"
    SAVE_TRACK_CHECKBOX = "Save track to file?"
    APPLY_STYLE_POINTS = "Apply style (QML) to points?"
    QML_POINTS = "Points QML:"
    APPLY_STYLE_TRACK = "Apply style (QML) to track?"
    QML_TRACK = "QML:"
    MRK_DROP_START = "MRK file detected. Starting conversion."
    CONVERT_FILE_SUCCESS = "File converted successfully."
    LOADED_EXISTING_GPKG = "Existing GPKG outputs loaded successfully."
    CONVERT_FILE_ERROR = "Failed to convert file."
    REPORT_METADATA_TITLE = "Metadata Report"
    REPORT_METADATA_TOOLTIP = (
        "Lists temporary metadata JSON files and regenerates the HTML report.\n"
        "Also provides a shortcut to open the reports folder."
    )
    PHOTO_VECTORIZATION_TITLE = "Photo Vectorization"
    PHOTO_VECTORIZATION_TOOLTIP = (
        "Generates a vector layer from photos and optionally a report with the extracted data."
    )
    REFRESH_JSON_LIST = "Refresh JSON list"
    OPEN_REPORTS_FOLDER = "Open reports folder"
    OPEN_JSONS_FOLDER = "Open JSON folder"
    VECTOR_WITHOUT_MRK_BLOCK_TITLE = "Generate Vector Without MRK"
    PHOTO_FOLDER = "Photo folder:"
    VECTORIZE_PHOTOS = "Generate photo vector"
    PHOTOS_WITHOUT_MRK_LAYER_NAME = "Photos_Without_MRK"
    NO_JSON_FOUND = "No temporary JSON files were found."

    # plugins/SettingsPlugin.py
    SETTINGS_TITLE = "Cadmus Settings"
    SETTINGS_TOOLTIP = (
        "Opens Cadmus global settings.\n"
        "Allows configuring the default vector calculation method,\n"
        "field precision, and feature threshold\n"
        "for asynchronous processing."
    )
    ELLIPSOIDAL = "Ellipsoidal"
    CARTESIAN = "Cartesian"
    BOTH = "Both"

    # plugins/ReplaceInLayouts.py
    REPLACE_IN_LAYOUTS_TITLE = "Replace Text in Layouts"
    REPLACE_IN_LAYOUTS_TOOLTIP = (
        "Searches for text in layout labels\n"
        "and replaces it with the provided value.\n"
        "Supports partial replacement or full label overwrite\n"
        "when a match is found."
    )
    REPLACE_IN_LAYOUTS_SWAP = "Swap"
    REPLACE_IN_LAYOUTS_RUN = "Run replacement"

    # plugins/LoadFolderLayers.py
    LOAD_FOLDER_LAYERS_TITLE = "Load Folder Layers"
    LOAD_FOLDER_LAYERS_TOOLTIP = (
        "Batch loads vector and raster files from a folder\n"
        "and its subfolders into the QGIS project.\n"
        "Supports file type filtering, duplicate avoidance,\n"
        "and layer grouping based on folder structure."
    )

    # plugins/GenerateTrailPlugin.py
    GENERATE_TRAIL_TITLE = "Generate Machine Trail"
    GENERATE_TRAIL_TOOLTIP = (
        "Generates the coverage area of an implement from a line layer.\n"
        "Converts the given width to the layer unit,\n"
        "applies a buffer using half of the value,\n"
        "and creates a new layer with the resulting trail."
    )

    # plugins/CopyAttributesPlugin.py
    COPY_ATTRIBUTES_TITLE = "Copy Vector Attributes"
    COPY_ATTRIBUTES_TOOLTIP = (
        "Copies the field structure from a source vector layer\n"
        "to a target vector layer.\n"
        "Allows selecting which attributes to create and handling\n"
        "name conflicts when fields already exist."
    )

    # plugins/ExportAllLayouts.py
    EXPORT_ALL_LAYOUTS_TITLE = "Export All Layouts"
    EXPORT_ALL_LAYOUTS_TOOLTIP = (
        "Exports all project layouts to PDF, PNG, or both.\n"
        "Can merge generated PDFs into a single file,\n"
        "convert PNGs into PDF, and control file overwrite\n"
        "in the output folder."
    )

    # plugins/VectorMultipartPlugin.py
    CONVERTER_MULTIPART_TITLE = "Convert Multipart"
    CONVERTER_MULTIPART_TOOLTIP = (
        "Processes multipart features in the active layer\n"
        "and splits them into single-part features.\n"
        "Can operate on selected features only\n"
        "or the entire layer, preserving attributes."
    )

    # plugins/CoordClickTool.py
    COORD_CLICK_TOOL_TITLE = "Capture Coordinates"
    COORD_CLICK_TOOL_TOOLTIP = (
        "Click on the map to retrieve point coordinates.\n"
        "Opens a dialog with WGS84, UTM, approximate elevation,\n"
        "and estimated address, along with copy options\n"
        "to the clipboard."
    )

    # core/ToolRegistry.py
    RESTART_QGIS_TITLE = "Save, Close and Reopen Project"
    RESTART_QGIS_TOOLTIP = (
        "Saves the current project, closes QGIS, and reopens it.\n"
        "Useful for recovering sessions after crashes\n"
        "or visual glitches without losing work."
    )
    LOGCAT_TITLE = "Log Viewer"
    LOGCAT_TOOLTIP = (
        "Opens the plugin log viewer.\n"
        "Allows inspecting messages, errors, and internal events\n"
        "recorded by Cadmus."
    )
    ABOUT_DIALOG_TOOLTIP = (
        f"Opens the {ABOUT_CADMUS} window of {APP_NAME}.\n"
        "Displays general information about the plugin,\n"
        "such as version, author, and project context."
    )
    VECTOR_FIELDS_TITLE = "Calculate Vector Fields"
    VECTOR_FIELDS_TOOLTIP = (
        "Automatically calculates vector fields such as area,\n"
        "length, or X/Y coordinates in the active layer.\n"
        "Useful for generating technical attributes\n"
        "without manual field editing."
    )
    REMOVE_KML_FIELDS_TITLE = "Remove KML Fields"
    REMOVE_KML_FIELDS_TOOLTIP = (
        "Removes typical KML attribute fields from the active layer.\n"
        "The tool only runs when the layer is already in edit mode\n"
        "and never saves or leaves edit mode."
    )
    DIVIDE_POINTS_BY_STRIPS_TITLE = "Split Point Vector by Strips"
    DIVIDE_POINTS_BY_STRIPS_TOOLTIP = (
        "Prepares the configuration used to segment a point layer into strips.\n"
        "In this first stage the tool registers the interface,\n"
        "organizes operational and sensitivity parameters,\n"
        "and leaves execution ready for the next implementation phase."
    )
    DIVIDE_POINTS_BY_STRIPS_INTRO = (
        "Configure the point layer and the initial parameters for strip division."
    )
    OPERATIONAL_PARAMETERS = "Operational Parameters"
    SENSITIVITY_PARAMETERS = "Sensitivity Parameters"
    UNIQUE_SEQUENTIAL_ID_FIELD = "Unique/sequential ID field"
    TIMESTAMP_FIELD = "Timestamp field"
    EXPECTED_POINT_FREQUENCY_SECONDS = "Expected point frequency (s)"
    EXPECTED_LATERAL_WIDTH_METERS = "Expected lateral width (m)"
    AZIMUTH_MOVING_WINDOW = "Azimuth moving window"
    LIGHT_AZIMUTH_DEVIATION_THRESHOLD = "Light azimuth deviation threshold (degrees)"
    SEVERE_AZIMUTH_DEVIATION_THRESHOLD = "Severe azimuth deviation threshold (degrees)"
    MINIMUM_BREAK_SCORE = "Minimum break score"
    MINIMUM_POINT_COUNT = "Minimum point count"
    TIME_TOLERANCE_MULTIPLIER = "Time tolerance (multiplier)"
    SELECT_POINT_VECTOR_LAYER = "Select a point vector layer."
    SELECT_FILE_BASED_POINT_LAYER = "Select a file-based point layer."
    SELECT_REQUIRED_FIELDS = "Select the required ID and timestamp fields."
    SAVE_AND_STOP_EDITING_LAYER = "Save and stop editing the layer before running this tool."
    SHOT_SEGMENTATION_COMPLETED = (
        "Segmentation completed. Points: {total_points} | Shots: {total_shots} | Valid: {valid_shots} | Invalid: {invalid_shots}"
    )
    SHOT_SEGMENTATION_BUFFER_COMPLETED = (
        "Segmentation completed in the edit buffer. Points: {total_points} | Shots: {total_shots} | Valid: {valid_shots} | Invalid: {invalid_shots}"
    )
    DIVIDE_POINTS_BY_STRIPS_UI_ONLY_MESSAGE = (
        "The interface is ready. The strip division routine will be implemented in the next stage."
    )
