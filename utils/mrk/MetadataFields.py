# -*- coding: utf-8 -*-

from typing import Dict, Iterable, List, Optional

from ...core.model.Field import Field
from ..adapter.StringAdapter import StringAdapter
from ...core.enum import MetadataFieldKey


class MetadataFields:
    EXIF_FIELDS = {
        MetadataFieldKey.FILE: Field(
            normalized="File",
            core="os",
            label="File",
            attribute="File",
            description="Nome do arquivo de imagem. [File]",
            level=3,
        ),
        MetadataFieldKey.PATH: Field(
            normalized="Path",
            core="os",
            label="Path",
            attribute="Path",
            description="Caminho completo do arquivo de imagem. [Path]",
            level=3,
        ),
        MetadataFieldKey.FORMAT: Field(
            normalized="Format",
            core="os",
            label="Format",
            attribute="FormatMod",
            description="Formato e modo de cor da imagem. [FormatMod]",
            level=3,
        ),
        MetadataFieldKey.SIZE_MB: Field(
            normalized="SizeMb",
            core="os",
            label="Size MB",
            attribute="SizeMB",
            description="Tamanho do arquivo em megabytes. [SizeMB]",
            level=3,
        ),
        MetadataFieldKey.GPS_MAP_DATUM: Field(
            normalized="EXIF:GPSInfo:GPSMapDatum",
            core="EXIF",
            label="GPS Map Datum",
            attribute="GPSDatum",
            description="Datum geodesico usado nas coordenadas GPS. [GPSDatum]",
            level=3,
        ),
        MetadataFieldKey.MODEL: Field(
            normalized="EXIF:Model",
            core="EXIF",
            label="Model",
            attribute="Model",
            description="Modelo da camera que capturou a imagem. [Model]",
            level=3,
        ),
        MetadataFieldKey.SOFTWARE: Field(
            normalized="EXIF:Software",
            core="EXIF",
            label="Software",
            attribute="Firmware",
            description="Software ou firmware gravado no metadado. [Firmware]",
            level=3,
        ),
        MetadataFieldKey.X_RESOLUTION: Field(
            normalized="EXIF:XResolution",
            core="EXIF",
            label="X Resolution",
            attribute="DPIWidth",
            description="Resolucao horizontal informada no EXIF (DPI). [DPIWidth]",
            level=3,
        ),
        MetadataFieldKey.Y_RESOLUTION: Field(
            normalized="EXIF:YResolution",
            core="EXIF",
            label="Y Resolution",
            attribute="DPIHeight",
            description="Resolucao vertical informada no EXIF (DPI). [DPIHeight]",
            level=3,
        ),
        MetadataFieldKey.SHUTTER_SPEED_VALUE: Field(
            normalized="EXIF:ShutterSpeedValue",
            core="EXIF",
            label="Shutter Speed Value",
            attribute="ShutterSp",
            description="Velocidade do obturador registrada no EXIF. [ShutterSp]",
            level=3,
        ),
        MetadataFieldKey.DATE_TIME_ORIGINAL: Field(
            normalized="EXIF:DateTimeOriginal",
            core="EXIF",
            label="Date Time Original",
            attribute="DateTime",
            description="Data e hora original da captura. [DateTime]",
            level=3,
        ),
        MetadataFieldKey.APERTURE_VALUE: Field(
            normalized="EXIF:ApertureValue",
            core="EXIF",
            label="Aperture Value",
            attribute="ApertureV",
            description="Valor de abertura usado na captura. [ApertureV]",
            level=3,
        ),
        MetadataFieldKey.MAX_APERTURE_VALUE: Field(
            normalized="EXIF:MaxApertureValue",
            core="EXIF",
            label="Max Aperture Value",
            attribute="MaxApertV",
            description="Maior abertura disponivel da lente. [MaxApertV]",
            level=3,
        ),
        MetadataFieldKey.LIGHT_SOURCE: Field(
            normalized="EXIF:LightSource",
            core="EXIF",
            label="Light Source",
            attribute="LightSour",
            description="Codigo da fonte de iluminacao da cena. [LightSour]",
            level=3,
        ),
        MetadataFieldKey.FOCAL_LENGTH: Field(
            normalized="EXIF:FocalLength",
            core="EXIF",
            label="Focal Length",
            attribute="FocalLeng",
            description="Distancia focal da lente em mm. [FocalLeng]",
            level=3,
        ),
        MetadataFieldKey.EXIF_IMAGE_WIDTH: Field(
            normalized="EXIF:ExifImageWidth",
            core="EXIF",
            label="EXIF Image Width",
            attribute="WidthPX",
            description="Largura da imagem em pixels (EXIF). [WidthPX]",
            level=3,
        ),
        MetadataFieldKey.EXIF_IMAGE_HEIGHT: Field(
            normalized="EXIF:ExifImageHeight",
            core="EXIF",
            label="EXIF Image Height",
            attribute="HeightPX",
            description="Altura da imagem em pixels (EXIF). [HeightPX]",
            level=3,
        ),
        MetadataFieldKey.EXPOSURE_TIME: Field(
            normalized="EXIF:ExposureTime",
            core="EXIF",
            label="Exposure Time",
            attribute="ExpTime",
            description="Tempo de exposicao da foto em segundos. [ExpTime]",
            level=3,
        ),
        MetadataFieldKey.F_NUMBER: Field(
            normalized="EXIF:FNumber",
            core="EXIF",
            label="F Number",
            attribute="FNumber",
            description="Numero f usado na captura. [FNumber]",
            level=3,
        ),
        MetadataFieldKey.EXPOSURE_PROGRAM: Field(
            normalized="EXIF:ExposureProgram",
            core="EXIF",
            label="Exposure Program",
            attribute="ExpProg",
            description="Programa de exposicao selecionado pela camera. [ExpProg]",
            level=3,
        ),
        MetadataFieldKey.ISO_SPEED_RATINGS: Field(
            normalized="EXIF:ISOSpeedRatings",
            core="EXIF",
            label="ISO Speed Ratings",
            attribute="ISOSpeed",
            description="Sensibilidade ISO usada na captura. [ISOSpeed]",
            level=3,
        ),
        MetadataFieldKey.EXPOSURE_MODE: Field(
            normalized="EXIF:ExposureMode",
            core="EXIF",
            label="Exposure Mode",
            attribute="ExpMode",
            description="Modo de exposicao configurado na camera. [ExpMode]",
            level=3,
        ),
        MetadataFieldKey.LENS_SPECIFICATION: Field(
            normalized="EXIF:LensSpecification",
            core="EXIF",
            label="Lens Specification",
            attribute="Lens",
            description="Faixa focal e de abertura da lente. [Lens]",
            level=3,
        ),
        MetadataFieldKey.DIGITAL_ZOOM_RATIO: Field(
            normalized="EXIF:DigitalZoomRatio",
            core="EXIF",
            label="Digital Zoom Ratio",
            attribute="ZoomRatio",
            description="Razao de zoom digital aplicada na captura. [ZoomRatio]",
            level=3,
        ),
        MetadataFieldKey.EXIF_SHARPNESS: Field(
            normalized="EXIF:Sharpness",
            core="EXIF",
            label="EXIF Sharpness",
            attribute="Sharpness",
            description="Nivel de nitidez da imagem mapeado pelo EXIF. [Sharpness]",
            level=3,
        ),
        MetadataFieldKey.EXIF_CONTRAST: Field(
            normalized="EXIF:Contrast",
            core="EXIF",
            label="EXIF Contrast",
            attribute="Contrast",
            description="Nivel de contraste aplicado na captura. [Contrast]",
            level=3,
        ),
        MetadataFieldKey.EXIF_SATURATION: Field(
            normalized="EXIF:Saturation",
            core="EXIF",
            label="EXIF Saturation",
            attribute="Saturation",
            description="Nivel de saturacao de cor da imagem. [Saturation]",
            level=3,
        ),
        MetadataFieldKey.EXIF_FLASH_PIX_VERSION: Field(
            normalized="EXIF:FlashPixVersion",
            core="EXIF",
            label="EXIF Flash Pix Version",
            attribute="FlashPixVer",
            description="Versao FlashPix gravada no EXIF. [FlashPixVer]",
            level=3,
        ),
        MetadataFieldKey.EXIF_COLOR_SPACE: Field(
            normalized="EXIF:ColorSpace",
            core="EXIF",
            label="EXIF Color Space",
            attribute="ColorSpace",
            description="Espaco de cor utilizado na captura da imagem. [ColorSpace]",
            level=3,
        ),
    }

    DJI_XMP_FIELDS = {
        MetadataFieldKey.GPS_STATUS: Field(
            normalized="EXIF:GPSInfo:GPSStatus",
            core="xmp_bloco_1",
            label="GPS Status",
            attribute="GpsStatus",
            description="Status do GPS no momento da foto. [GpsStatus]",
            level=3,
        ),
        MetadataFieldKey.ALTITUDE_TYPE: Field(
            normalized="xmp_bloco_1:drone-dji:AltitudeType",
            core="xmp_bloco_1",
            label="Altitude Type",
            attribute="Ytype",
            description="Tipo de altitude registrado pelo drone. [Ytype]",
            level=3,
        ),
        MetadataFieldKey.GPS_LATITUDE: Field(
            normalized="EXIF:GPSInfo:GPSLatitude",
            core="xmp_bloco_1",
            label="GPS Latitude",
            attribute="GpsLat",
            description="Latitude GPS da aeronave na captura. [GpsLat]",
            level=3,
        ),
        MetadataFieldKey.GPS_LONGITUDE: Field(
            normalized="EXIF:GPSInfo:GPSLongitude",
            core="xmp_bloco_1",
            label="GPS Longitude",
            attribute="GPSLong",
            description="Longitude GPS da aeronave na captura. [GPSLong]",
            level=3,
        ),
        MetadataFieldKey.ABSOLUTE_ALTITUDE: Field(
            normalized="xmp_bloco_1:drone-dji:AbsoluteAltitude",
            core="xmp_bloco_1",
            label="Absolute Altitude",
            attribute="AbsY",
            description="Altitude absoluta da aeronave. [AbsY]",
            level=3,
        ),
        MetadataFieldKey.RELATIVE_ALTITUDE: Field(
            normalized="xmp_bloco_1:drone-dji:RelativeAltitude",
            core="xmp_bloco_1",
            label="Relative Altitude",
            attribute="RelativeY",
            description="Altitude relativa ao ponto de decolagem. [RelativeY]",
            level=3,
        ),
        MetadataFieldKey.GIMBAL_ROLL_DEGREE: Field(
            normalized="xmp_bloco_1:drone-dji:GimbalRollDegree",
            core="xmp_bloco_1",
            label="Gimbal Roll Degree",
            attribute="GimbRoll",
            description="Angulo de rolagem do gimbal em graus. [GimbRoll]",
            level=3,
        ),
        MetadataFieldKey.GIMBAL_YAW_DEGREE: Field(
            normalized="xmp_bloco_1:drone-dji:GimbalYawDegree",
            core="xmp_bloco_1",
            label="Gimbal Yaw Degree",
            attribute="GimbYaw",
            description="Angulo de yaw do gimbal em graus. [GimbYaw]",
            level=3,
        ),
        MetadataFieldKey.GIMBAL_PITCH_DEGREE: Field(
            normalized="xmp_bloco_1:drone-dji:GimbalPitchDegree",
            core="xmp_bloco_1",
            label="Gimbal Pitch Degree",
            attribute="GimbPitch",
            description="Angulo de pitch do gimbal em graus. [GimbPitch]",
            level=3,
        ),
        MetadataFieldKey.FLIGHT_ROLL_DEGREE: Field(
            normalized="xmp_bloco_1:drone-dji:FlightRollDegree",
            core="xmp_bloco_1",
            label="Flight Roll Degree",
            attribute="DroneRoll",
            description="Angulo de rolagem da aeronave em graus. [DroneRoll]",
            level=3,
        ),
        MetadataFieldKey.FLIGHT_YAW_DEGREE: Field(
            normalized="xmp_bloco_1:drone-dji:FlightYawDegree",
            core="xmp_bloco_1",
            label="Flight Yaw Degree",
            attribute="DroneYaw",
            description="Angulo de yaw da aeronave em graus. [DroneYaw]",
            level=3,
        ),
        MetadataFieldKey.FLIGHT_PITCH_DEGREE: Field(
            normalized="xmp_bloco_1:drone-dji:FlightPitchDegree",
            core="xmp_bloco_1",
            label="Flight Pitch Degree",
            attribute="DronePitc",
            description="Angulo de pitch da aeronave em graus. [DronePitc]",
            level=3,
        ),
        MetadataFieldKey.FLIGHT_X_SPEED: Field(
            normalized="xmp_bloco_1:drone-dji:FlightXSpeed",
            core="xmp_bloco_1",
            label="Flight X Speed",
            attribute="XSpeed",
            description="Velocidade da aeronave no eixo X. [XSpeed]",
            level=3,
        ),
        MetadataFieldKey.FLIGHT_Y_SPEED: Field(
            normalized="xmp_bloco_1:drone-dji:FlightYSpeed",
            core="xmp_bloco_1",
            label="Flight Y Speed",
            attribute="YSpeed",
            description="Velocidade da aeronave no eixo Y. [YSpeed]",
            level=3,
        ),
        MetadataFieldKey.FLIGHT_Z_SPEED: Field(
            normalized="xmp_bloco_1:drone-dji:FlightZSpeed",
            core="xmp_bloco_1",
            label="Flight Z Speed",
            attribute="ZSpeed",
            description="Velocidade da aeronave no eixo Z. [ZSpeed]",
            level=3,
        ),
        MetadataFieldKey.RTK_FLAG: Field(
            normalized="xmp_bloco_1:drone-dji:RtkFlag",
            core="xmp_bloco_1",
            label="RTK Flag",
            attribute="RtkFlag",
            description="Indicador de qualidade/correcao RTK. [RtkFlag]",
            level=3,
        ),
        MetadataFieldKey.RTK_STD_LON: Field(
            normalized="xmp_bloco_1:drone-dji:RtkStdLon",
            core="xmp_bloco_1",
            label="RTK Std Lon",
            attribute="RtkStdLon",
            description="Desvio padrao RTK na longitude. [RtkStdLon]",
            level=3,
        ),
        MetadataFieldKey.RTK_STD_LAT: Field(
            normalized="xmp_bloco_1:drone-dji:RtkStdLat",
            core="xmp_bloco_1",
            label="RTK Std Lat",
            attribute="RtkStdLat",
            description="Desvio padrao RTK na latitude. [RtkStdLat]",
            level=3,
        ),
        MetadataFieldKey.RTK_STD_HGT: Field(
            normalized="xmp_bloco_1:drone-dji:RtkStdHgt",
            core="xmp_bloco_1",
            label="RTK Std Hgt",
            attribute="RtkStdHgt",
            description="Desvio padrao RTK na altitude. [RtkStdHgt]",
            level=3,
        ),
        MetadataFieldKey.RTK_DIFF_AGE: Field(
            normalized="xmp_bloco_1:drone-dji:RtkDiffAge",
            core="xmp_bloco_1",
            label="RTK Diff Age",
            attribute="RtkDifAge",
            description="Tempo desde a ultima correcao RTK. [RtkDifAge]",
            level=3,
        ),
        MetadataFieldKey.DEWARP_FLAG: Field(
            normalized="xmp_bloco_1:drone-dji:DewarpFlag",
            core="xmp_bloco_1",
            label="Dewarp Flag",
            attribute="Dewarp",
            description="Estado da correcao de distorcao (dewarp). [Dewarp]",
            level=3,
        ),
        MetadataFieldKey.UTC_AT_EXPOSURE: Field(
            normalized="xmp_bloco_1:drone-dji:UTCAtExposure",
            core="xmp_bloco_1",
            label="UTC At Exposure",
            attribute="UTCTime",
            description="Horario UTC exato do momento da exposicao. [UTCTime]",
            level=3,
        ),
        MetadataFieldKey.SHUTTER_COUNT: Field(
            normalized="xmp_bloco_1:drone-dji:ShutterCount",
            core="xmp_bloco_1",
            label="Shutter Count",
            attribute="ShotCount",
            description="Total de disparos acumulados da camera. [ShotCount]",
            level=3,
        ),
        MetadataFieldKey.FOCUS_DISTANCE: Field(
            normalized="xmp_bloco_1:drone-dji:FocusDistance",
            core="xmp_bloco_1",
            label="Focus Distance",
            attribute="FocusDist",
            description="Distancia de foco usada na captura. [FocusDist]",
            level=3,
        ),
        MetadataFieldKey.CAMERA_SERIAL_NUMBER: Field(
            normalized="xmp_bloco_1:drone-dji:CameraSerialNumber",
            core="xmp_bloco_1",
            label="Camera Serial Number",
            attribute="CameraID",
            description="Numero serial da camera. [CameraID]",
            level=3,
        ),
        MetadataFieldKey.DRONE_MODEL: Field(
            normalized="xmp_bloco_1:drone-dji:DroneModel",
            core="xmp_bloco_1",
            label="Drone Model",
            attribute="DronModel",
            description="Modelo da aeronave/drone. [DronModel]",
            level=3,
        ),
        MetadataFieldKey.DRONE_SERIAL_NUMBER: Field(
            normalized="xmp_bloco_1:drone-dji:DroneSerialNumber",
            core="xmp_bloco_1",
            label="Drone Serial Number",
            attribute="DroneID",
            description="Numero serial da aeronave/drone. [DroneID]",
            level=3,
        ),
        MetadataFieldKey.CAPTURE_UUID: Field(
            normalized="xmp_bloco_1:drone-dji:CaptureUUID",
            core="xmp_bloco_1",
            label="Capture UUID",
            attribute="CaptureID",
            description="Identificador unico do conjunto de captura. [CaptureID]",
            level=3,
        ),
        MetadataFieldKey.PICTURE_QUALITY: Field(
            normalized="xmp_bloco_1:drone-dji:PictureQuality",
            core="xmp_bloco_1",
            label="Picture Quality",
            attribute="ImgQualit",
            description="Nivel de qualidade/compressao da imagem. [ImgQualit]",
            level=3,
        ),
        MetadataFieldKey.SEGMENTOS_TOTAL: Field(
            normalized="JPEG:SegmentosTotal",
            core="xmp_bloco_1",
            label="Segmentos Total",
            attribute="Segments",
            description="Quantidade total de segmentos JPEG lidos. [Segments]",
            level=3,
        ),
        MetadataFieldKey.SENSOR_TEMPERATURE: Field(
            normalized="xmp_bloco_1:drone-dji:SensorTemperature",
            core="xmp_bloco_1",
            label="Sensor Temperature",
            attribute="SensTemp",
            description="Temperatura do sensor da camera. [SensTemp]",
            level=3,
        ),
        MetadataFieldKey.LRF_STATUS: Field(
            normalized="xmp_bloco_1:drone-dji:LRFStatus",
            core="xmp_bloco_1",
            label="LRF Status",
            attribute="LRFStatus",
            description="Status do laser range finder (LRF). [LRFStatus]",
            level=3,
        ),
        MetadataFieldKey.LRF_TARGET_DISTANCE: Field(
            normalized="xmp_bloco_1:drone-dji:LRFTargetDistance",
            core="xmp_bloco_1",
            label="LRF Target Distance",
            attribute="LRFDist",
            description="Distancia medida pelo LRF ate o alvo central. [LRFDist]",
            level=3,
        ),
        MetadataFieldKey.LRF_TARGET_LON: Field(
            normalized="xmp_bloco_1:drone-dji:LRFTargetLon",
            core="xmp_bloco_1",
            label="LRF Target Lon",
            attribute="LRFLong",
            description="Longitude do alvo medida pelo LRF. [LRFLong]",
            level=3,
        ),
        MetadataFieldKey.LRF_TARGET_LAT: Field(
            normalized="xmp_bloco_1:drone-dji:LRFTargetLat",
            core="xmp_bloco_1",
            label="LRF Target Lat",
            attribute="LRFLati",
            description="Latitude do alvo medida pelo LRF. [LRFLati]",
            level=3,
        ),
        MetadataFieldKey.LRF_TARGET_ALT: Field(
            normalized="xmp_bloco_1:drone-dji:LRFTargetAlt",
            core="xmp_bloco_1",
            label="LRF Target Alt",
            attribute="LRFY",
            description="Altitude relativa do alvo medida pelo LRF. [LRFY]",
            level=3,
        ),
        MetadataFieldKey.LRF_TARGET_ABS_ALT: Field(
            normalized="xmp_bloco_1:drone-dji:LRFTargetAbsAlt",
            core="xmp_bloco_1",
            label="LRF Target Abs Alt",
            attribute="LrfAbsAlt",
            description="Altitude absoluta do alvo medida pelo LRF. [LrfAbsAlt]",
            level=3,
        ),
        MetadataFieldKey.WHITE_BALANCE_CCT: Field(
            normalized="xmp_bloco_1:drone-dji:WhiteBalanceCCT",
            core="xmp_bloco_1",
            label="White Balance CCT",
            attribute="WhiteBlc",
            description="Temperatura de cor (Kelvin) no balanco de branco. [WhiteBlc]",
            level=3,
        ),
        MetadataFieldKey.SENSOR_FPS: Field(
            normalized="xmp_bloco_1:drone-dji:SensorFPS",
            core="xmp_bloco_1",
            label="Sensor FPS",
            attribute="SensorFPS",
            description="Taxa de amostragem do sensor em FPS. [SensorFPS]",
            level=3,
        ),
        MetadataFieldKey.RECOMMENDED_EXPOSURE_INDEX: Field(
            normalized="EXIF:RecommendedExposureIndex",
            core="xmp_bloco_1",
            label="Recommended Exposure Index",
            attribute="REI",
            description="Indice de exposicao recomendado (REI). [REI]",
            level=3,
        ),
        MetadataFieldKey.LENS_POSITION: Field(
            normalized="xmp_bloco_1:drone-dji:LensPosition",
            core="xmp_bloco_1",
            label="Lens Position",
            attribute="LensPosit",
            description="Posicao da lente no momento da captura. [LensPosit]",
            level=3,
        ),
        MetadataFieldKey.LENS_TEMPERATURE: Field(
            normalized="xmp_bloco_1:drone-dji:LensTemperature",
            core="xmp_bloco_1",
            label="Lens Temperature",
            attribute="LensTemp",
            description="Temperatura da lente no momento da captura. [LensTemp]",
            level=3,
        ),
    }

    REQUIRED_FIELDS = {**EXIF_FIELDS, **DJI_XMP_FIELDS}

    CUSTOM_FIELDS = {
        MetadataFieldKey.FILE_TYPE: Field(
            normalized="Custom:FileType",
            core="custom",
            label="File Type",
            attribute="FileType",
            description="Tipo/Extensao do arquivo de imagem (ex.: .JPG). [FileType]",
            level=5,
        ),
        MetadataFieldKey.DT_FULL: Field(
            normalized="Custom:DtFull",
            core="custom",
            label="Date Time Full",
            attribute="DateTmFul",
            description="Data/hora compacta no formato YYYYMMDDHHMM. [DateTmFul]",
            level=5,
        ),
        MetadataFieldKey.DT_DATE: Field(
            normalized="Custom:DtDate",
            core="custom",
            label="Date Only",
            attribute="DateOnly",
            description="Data compacta no formato YYYYMMDD. [DateOnly]",
            level=5,
        ),
        MetadataFieldKey.DT_TIME: Field(
            normalized="Custom:DtTime",
            core="custom",
            label="Time Only",
            attribute="TimeOnly",
            description="Horario compacto no formato HHMM. [TimeOnly]",
            level=5,
        ),
        MetadataFieldKey.FLIGHT_NUMBER: Field(
            normalized="Custom:FlightNumber",
            core="custom",
            label="Flight Number",
            attribute="DrvFNum",
            description="Numero do voo derivado do MRK. [DrvFNum]",
            level=5,
        ),
        MetadataFieldKey.FLIGHT_NAME: Field(
            normalized="Custom:FlightName",
            core="custom",
            label="Flight Name",
            attribute="DrvFNam",
            description="Nome do voo derivado do MRK. [DrvFNam]",
            level=5,
        ),
        MetadataFieldKey.FOLDER_LEVEL_1: Field(
            normalized="Custom:FolderLevel1",
            core="custom",
            label="Folder Level 1",
            attribute="FolderL1",
            description="Primeiro nivel de pasta do voo. [FolderL1]",
            level=5,
        ),
        MetadataFieldKey.FOLDER_LEVEL_2: Field(
            normalized="Custom:FolderLevel2",
            core="custom",
            label="Folder Level 2",
            attribute="FolderL2",
            description="Segundo nivel de pasta do voo. [FolderL2]",
            level=5,
        ),
        MetadataFieldKey.GIMBAL_OFFSET: Field(
            normalized="xmp_bloco_1:drone-dji:GimbalOffset",
            core="custom",
            label="Gimbal Offset",
            attribute="GimOffset",
            description="Deslocamento angular mínimo do gimbal em relação à aeronave em graus (GimbalYawDegree - FlightYawDegree - 180, normalizado para menor ângulo). Valores: 0-180°. Valor referência: <1°. [GimOffset]",
            level=5,
        ),
        MetadataFieldKey.THREE_D_SPEED: Field(
            normalized="Custom:3DSpeed",
            core="custom",
            label="3 D Speed",
            attribute="3DSpeed",
            description="Velocidade total 3D da aeronave em m/s, calculada como sqrt(FlightXSpeed² + FlightYSpeed² + FlightZSpeed²). Valores: 0-50 m/s. Valor referência: <10 m/s para voos estáveis. [3DSpeed]",
            level=5,
        ),
        MetadataFieldKey.TIME_SINCE_PREVIOUS: Field(
            normalized="Custom:TimeSincePrevious",
            core="custom",
            label="Time Since Previous",
            attribute="TimePrv",
            description="Tempo em segundos desde a foto anterior. Valores: 0-120 s. Valor referência: 2-5 s para cadência ideal. [TimePrv]",
            level=5,
        ),
        MetadataFieldKey.GEODESIC_DISTANCE_PREVIOUS: Field(
            normalized="Custom:GeodesicDistancePrevious",
            core="custom",
            label="Geodesic Distance Previous",
            attribute="GeoDstP",
            description="Distância horizontal em metros entre posições GPS consecutivas (fórmula Haversine). Valores: 0-100 m. Valor referência: 20-50 m para sobreposição adequada. [GeoDstP]",
            level=5,
        ),
        MetadataFieldKey.DISTANCE_3D_PREVIOUS: Field(
            normalized="Custom:Distance3dPrevious",
            core="custom",
            label="Distance 3 D Previous",
            attribute="Dist3DP",
            description="Distância 3D em metros entre posições consecutivas (horizontal + altitude). Valores: 0-100 m. Valor referência: 20-50 m. [Dist3DP]",
            level=5,
        ),
        MetadataFieldKey.AVG_VELOCITY_BETWEEN_PHOTOS: Field(
            normalized="Custom:AvgVelocityBetweenPhotos",
            core="custom",
            label="Avg Velocity Between Photos",
            attribute="AvgVelB",
            description="Velocidade média em m/s entre fotos consecutivas. Valores: 0-20 m/s. Valor referência: 5-10 m/s. [AvgVelB]",
            level=5,
        ),
        MetadataFieldKey.LINEAR_VELOCITY_INSTANT: Field(
            normalized="Custom:LinearVelocityInstant",
            core="custom",
            label="Linear Velocity Instant",
            attribute="LinVelI",
            description="Velocidade instantânea 3D em m/s. Valores: 0-50 m/s. Valor referência: <10 m/s. [LinVelI]",
            level=5,
        ),
        MetadataFieldKey.DISPLACEMENT_DIRECTION: Field(
            normalized="Custom:DisplacementDirection",
            core="custom",
            label="Displacement Direction",
            attribute="DirDispl",
            description="Azimute do deslocamento em graus (0=Norte). Valores: 0-360°. Valor referência: varia por missão. [DirDispl]",
            level=5,
        ),
        MetadataFieldKey.INCIDENCE_ANGLE: Field(
            normalized="Custom:IncidenceAngle",
            core="custom",
            label="Incidence Angle",
            attribute="IncAngle",
            description="Ângulo de incidência em graus (ângulo entre câmera e vertical). Valores: 0-180°. Valor referência: <5° para nadir. [IncAngle]",
            level=5,
        ),
        MetadataFieldKey.ESTIMATED_COVERAGE: Field(
            normalized="Custom:EstimatedCoverage",
            core="custom",
            label="Estimated Coverage",
            attribute="EstCover",
            description="Tupla (largura, altura) em metros da cobertura estimada no solo. Valores: (0-200, 0-150) m. Valor referência: depende altitude. [EstCover]",
            level=5,
        ),
        MetadataFieldKey.PREDICTED_OVERLAP: Field(
            normalized="Custom:PredictedOverlap",
            core="custom",
            label="Predicted Overlap",
            attribute="PredOver",
            description="Percentual de sobreposição longitudinal com foto anterior. Valores: 0-100%. Valor referência: >60%. [PredOver]",
            level=5,
        ),
        MetadataFieldKey.RTK_EFFECTIVE_PRECISION: Field(
            normalized="Custom:RtkEffectivePrecision",
            core="custom",
            label="RTK Effective Precision",
            attribute="RTKPrec",
            description="Classificação textual da precisão RTK. Valores: Alta, Média, Baixa, Sem RTK. Valor referência: Alta. [RTKPrec]",
            level=5,
        ),
        MetadataFieldKey.IS_IDEAL_OVERLAP: Field(
            normalized="Custom:IsIdealOverlap",
            core="custom",
            label="Is Ideal Overlap",
            attribute="IdealOvl",
            description="Booleano indicando se sobreposição >=60%. Valores: True/False. Valor referência: True. [IdealOvl]",
            level=5,
        ),
        MetadataFieldKey.ABRUPT_CHANGE_FLAG: Field(
            normalized="Custom:AbruptChangeFlag",
            core="custom",
            label="Abrupt Change Flag",
            attribute="AbrChgF",
            description="Flag de mudança brusca (tempo ou distância >2x mediana). Valores: True/False. Valor referência: False. [AbrChgF]",
            level=5,
        ),
        MetadataFieldKey.GIMBAL_ANGULAR_VELOCITY: Field(
            normalized="Custom:GimbalAngularVelocity",
            core="custom",
            label="Gimbal Angular Velocity",
            attribute="GimAngV",
            description="Variação angular do gimbal em °/s. Valores: 0-100 °/s. Valor referência: <1 °/s. [GimAngV]",
            level=5,
        ),
        MetadataFieldKey.ORTHORECTIFICATION_POTENTIAL: Field(
            normalized="Custom:OrthorectificationPotential",
            core="custom",
            label="Orthorectification Potential",
            attribute="OrtoPot",
            description="Score de potencial para ortorretificação (0-100). Valores: 0-100. Valor referência: >80. [OrtoPot]",
            level=5,
        ),
        MetadataFieldKey.SHUTTER_LIFE_PCT: Field(
            normalized="Custom:ShutterLifePct",
            core="custom",
            label="Shutter Life Pct",
            attribute="ShutPct",
            description="% de vida útil do obturador. Valores: 0-100%. Valor referência: <50%. [ShutPct]",
            level=5,
        ),
        MetadataFieldKey.GROUND_SAMPLE_DISTANCE_CM: Field(
            normalized="Custom:GroundSampleDistanceCm",
            core="custom",
            label="Ground Sample Distance Cm",
            attribute="GsdCmPx",
            description="GSD em cm/pixel. Valores: 0-10 cm. Valor referência: <2 cm. [GsdCmPx]",
            level=5,
        ),
        MetadataFieldKey.TOTAL_HEAT_INDEX: Field(
            normalized="Custom:TotalHeatIndex",
            core="custom",
            label="Total Heat Index",
            attribute="HeatIdx",
            description="Índice térmico médio em °C. Valores: 20-60 °C. Valor referência: <40 °C. [HeatIdx]",
            level=5,
        ),
        MetadataFieldKey.SPEED_3D_KMH: Field(
            normalized="Custom:Speed3dKmh",
            core="custom",
            label="Speed 3 D Kmh",
            attribute="SpdKmH",
            description="Velocidade 3D do drone em km/h. Valores: 0-180 km/h. Valor referência: <36 km/h. [SpdKmH]",
            level=5,
        ),
        MetadataFieldKey.YAW_ALIGNMENT_ERROR: Field(
            normalized="Custom:YawAlignmentError",
            core="custom",
            label="Yaw Alignment Error",
            attribute="YawErr",
            description="Erro de alinhamento yaw em graus. Valores: 0-180°. Valor referência: <5°. [YawErr]",
            level=5,
        ),
        MetadataFieldKey.MOTION_BLUR_RISK: Field(
            normalized="Custom:MotionBlurRisk",
            core="custom",
            label="Motion Blur Risk",
            attribute="BlurRisk",
            description="Risco de motion blur em pixels. Valores: 0-5. Valor referência: <0.5. [BlurRisk]",
            level=5,
        ),
        MetadataFieldKey.EXPOSURE_VALUE_EV: Field(
            normalized="Custom:ExposureValueEv",
            core="custom",
            label="Exposure Value EV",
            attribute="EV",
            description="Valor de exposição EV. Valores: 8-16. Valor referência: 12-14. [EV]",
            level=5,
        ),
        MetadataFieldKey.LIGHT_SOURCE_CLASSIFICATION: Field(
            normalized="Custom:LightSourceClassification",
            core="custom",
            label="Light Source Classification",
            attribute="LSrcClass",
            description="Classificação textual da fonte de luz EXIF. Valores: Daylight, Fluorescent, etc. Valor referência: Daylight. [LSrcClass]",
            level=5,
        ),
        MetadataFieldKey.LIGHT_CONSISTENCY: Field(
            normalized="Custom:LightConsistency",
            core="custom",
            label="Light Consistency",
            attribute="LightCons",
            description="Consistência entre LightSource e CCT. Valores: Consistent, Inconsistent, Unknown. Valor referência: Consistent. [LightCons]",
            level=5,
        ),
        MetadataFieldKey.VERTICAL_STABILITY: Field(
            normalized="Custom:VerticalStability",
            core="custom",
            label="Vertical Stability",
            attribute="VertStb",
            description="Variação vertical em metros. Valores: 0-10 m. Valor referência: <1 m. [VertStb]",
            level=5,
        ),
        MetadataFieldKey.TRAJECTORY_SMOOTHNESS: Field(
            normalized="Custom:TrajectorySmoothness",
            core="custom",
            label="Trajectory Smoothness",
            attribute="TrajSmt",
            description="Diferença angular de direção em graus. Valores: 0-180°. Valor referência: <10°. [TrajSmt]",
            level=5,
        ),
        MetadataFieldKey.SPEED_VARIATION_INDEX: Field(
            normalized="Custom:SpeedVariationIndex",
            core="custom",
            label="Speed Variation Index",
            attribute="SpdVar",
            description="Índice de variação de velocidade (coeficiente de variação). Valores: 0-1. Valor referência: <0.1. [SpdVar]",
            level=5,
        ),
        MetadataFieldKey.RTK_STABILITY_SCORE: Field(
            normalized="Custom:RtkStabilityScore",
            core="custom",
            label="RTK Stability Score",
            attribute="RtkStab",
            description="Score de estabilidade RTK (0-100). Valores: 0-100. Valor referência: >90. [RtkStab]",
            level=5,
        ),
        MetadataFieldKey.CAPTURE_EFFICIENCY: Field(
            normalized="Custom:CaptureEfficiency",
            core="custom",
            label="Capture Efficiency",
            attribute="CapEff",
            description="Eficiência de captura (distância/cobertura). Valores: 0-1. Valor referência: 0.5-0.8. [CapEff]",
            level=5,
        ),
        MetadataFieldKey.PHOTOGRAMMETRY_QUALITY_INDEX: Field(
            normalized="Custom:PhotogrammetryQualityIndex",
            core="custom",
            label="Photogrammetry Quality Index",
            attribute="PQI",
            description="Índice de qualidade fotogramétrica (0-100). Valores: 0-100. Valor referência: >80. [PQI]",
            level=5,
        ),
        MetadataFieldKey.STRIP_ID: Field(
            normalized="Custom:StripId",
            core="custom",
            label="Strip ID",
            attribute="StripID",
            description="ID da faixa de voo. Valores: 1+. Valor referência: incremental. [StripID]",
            level=5,
        ),
    }

    MRK_FIELDS = {
        MetadataFieldKey.FOTO: Field(
            normalized="MRK:Foto",
            core="mrk",
            label="Photo Number",
            attribute="PhotoNum",
            description="Numero sequencial da foto vindo do MRK. [PhotoNum]",
            level=5,
        ),
        MetadataFieldKey.LAT: Field(
            normalized="MRK:Lat",
            core="mrk",
            label="Latitude",
            attribute="Latitude",
            description="Latitude extraida do arquivo MRK. [Latitude]",
            level=5,
        ),
        MetadataFieldKey.LON: Field(
            normalized="MRK:Lon",
            core="mrk",
            label="Longitude",
            attribute="Longitude",
            description="Longitude extraida do arquivo MRK. [Longitude]",
            level=5,
        ),
        MetadataFieldKey.ALT: Field(
            normalized="MRK:Alt",
            core="mrk",
            label="Altitude",
            attribute="Altitude",
            description="Altitude extraida do arquivo MRK. [Altitude]",
            level=5,
        ),
        MetadataFieldKey.DATE_NAME: Field(
            normalized="MRK:DateName",
            core="mrk",
            label="Date Name",
            attribute="DateName",
            description="Data identificada a partir do nome do MRK. [DateName]",
            level=5,
        ),
        MetadataFieldKey.MRK_FILE: Field(
            normalized="MRK:MrkFile",
            core="mrk",
            label="MRK File",
            attribute="MrkFile",
            description="Nome do arquivo MRK de origem. [MrkFile]",
            level=5,
        ),
        MetadataFieldKey.MRK_PATH: Field(
            normalized="MRK:MrkPath",
            core="mrk",
            label="MRK Path",
            attribute="MrkPath",
            description="Caminho completo do arquivo MRK de origem. [MrkPath]",
            level=5,
        ),
        MetadataFieldKey.MRK_FOLDER: Field(
            normalized="MRK:MrkFolder",
            core="mrk",
            label="MRK Folder",
            attribute="MrkFolder",
            description="Pasta absoluta de origem do ponto MRK. [MrkFolder]",
            level=5,
        ),
        MetadataFieldKey.FLIGHT_NUMBER: Field(
            normalized="MRK:FlightNumber",
            core="mrk",
            label="Flight Number",
            attribute="FlightNum",
            description="Numero do voo identificado no MRK. [FlightNum]",
            level=5,
        ),
        MetadataFieldKey.FLIGHT_NAME: Field(
            normalized="MRK:FlightName",
            core="mrk",
            label="Flight Name",
            attribute="FlightNam",
            description="Nome do voo identificado no MRK. [FlightNam]",
            level=5,
        ),
        MetadataFieldKey.FOLDER_LEVEL_1: Field(
            normalized="MRK:FolderLevel1",
            core="mrk",
            label="Folder Level 1",
            attribute="Folder1",
            description="Primeiro nivel de pasta no caminho do MRK. [Folder1]",
            level=5,
        ),
        MetadataFieldKey.FOLDER_LEVEL_2: Field(
            normalized="MRK:FolderLevel2",
            core="mrk",
            label="Folder Level 2",
            attribute="Folder2",
            description="Segundo nivel de pasta no caminho do MRK. [Folder2]",
            level=5,
        ),
    }

    @classmethod
    def all_fields(cls) -> Dict[str, Field]:
        fields: Dict[str, Field] = {}
        fields.update({key.value: field for key, field in cls.EXIF_FIELDS.items()})
        fields.update({key.value: field for key, field in cls.DJI_XMP_FIELDS.items()})
        fields.update({key.value: field for key, field in cls.CUSTOM_FIELDS.items()})
        fields.update({key.value: field for key, field in cls.MRK_FIELDS.items()})
        return fields

    @staticmethod
    def _to_pascal_case(value: str) -> str:
        if not value:
            return value
        parts = [part for part in str(value).split("_") if part]
        if not parts:
            return str(value)
        return "".join(part[:1].upper() + part[1:] for part in parts)

    @classmethod
    def exif_keys(cls) -> List[str]:
        return [key.value for key in cls.EXIF_FIELDS.keys()]

    @classmethod
    def xmp_keys(cls) -> List[str]:
        return [key.value for key in cls.DJI_XMP_FIELDS.keys()]

    @classmethod
    def required_keys(cls) -> List[str]:
        return [key.value for key in cls.EXIF_FIELDS.keys()] + [key.value for key in cls.DJI_XMP_FIELDS.keys()]

    @classmethod
    def custom_keys(cls) -> List[str]:
        return [key.value for key in cls.CUSTOM_FIELDS.keys()]

    @classmethod
    def mrk_keys(cls) -> List[str]:
        return [key.value for key in cls.MRK_FIELDS.keys()]

    @classmethod
    def key_to_attribute_map(cls) -> Dict[str, str]:
        return {key.value: field.attribute for key, field in cls.all_fields().items()}

    @classmethod
    def sanitize_field_name(cls, raw_field_name: str) -> Optional[str]:
        """
        Mapeia nomes de campos brutos/ilegais para campos canonizados em MetadataFields.

        Realiza as seguintes normalizacoes:
        1. Remove espacos e converte para PascalCase
        2. Remove prefixos de namespace (xmp:, drone-dji:, crs:, tiff:, rdf:)
        3. Mapeia campos de sistema (arquivo, caminho, etc.) para canonicos
        4. Valida contra MetadataFields.all_fields()

        Args:
            raw_field_name: Nome bruto do campo (ex: "xmp:CreateDate", "arquivo", "tamanho_mb")

        Returns:
            Nome canonizado do atributo se mapeado com sucesso, None caso contrario
        """
        if not raw_field_name or not isinstance(raw_field_name, str):
            return None

        # Remove espacos
        normalized = raw_field_name.strip()

        # Remove prefixos de namespace
        namespace_prefixes = (
            "xmp:",
            "drone-dji:",
            "crs:",
            "tiff:",
            "rdf:",
            "EXIF:",
            "GPS:",
        )
        for prefix in namespace_prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
                break

        # Mapeamento especial para campos de sistema
        field_mappings = {
            "arquivo": "File",
            "caminho": "Path",
            "tamanho_mb": "SizeMb",
            "data_criacao": "DateTime",
            "dt_criacao": "DateTime",
            "os_date": "DateTime",
            "folder_path": "FolderLevel1",
            "voo_id": "FlightNumber",
            "width_px": "ExifImageWidth",
            "height_px": "ExifImageHeight",
            "coverage_width": "EstimatedCoverage",
            # Variantes de nomes EXIF brutos
            "gpsstatus": "GpsStatus",
            "gpsversion": "GpsStatus",
            # Variantes de datas
            "createdate": "DateTime",
            "modifydate": "DateTime",
        }

        # Verifica mapemento especial (case-insensitive)
        normalized_lower = normalized.lower()
        if normalized_lower in field_mappings:
            return field_mappings[normalized_lower]

        # Tenta encontrar nos campos canonicos
        all_fields_dict = cls.all_fields()

        # Primeiro: busca exata (case-sensitive)
        if normalized in all_fields_dict:
            return all_fields_dict[normalized].attribute

        # Segundo: busca case-insensitive
        normalized_lower = normalized.lower()
        for field_name, field_obj in all_fields_dict.items():
            if field_name.lower() == normalized_lower:
                return field_obj.attribute

        # Terceiro: tenta conversao para PascalCase
        pascal_case = cls._to_pascal_case(
            normalized.replace(" ", "_").replace("-", "_")
        )
        for field_name, field_obj in all_fields_dict.items():
            if field_name.lower() == pascal_case.lower():
                return field_obj.attribute

        # Nenhuma correspondencia encontrada
        return None

    @classmethod
    def is_authorized_field(cls, field_name: str) -> bool:
        """
        Verifica se um nome de campo e um dos campos autorizados em MetadataFields.

        Args:
            field_name: Nome do campo a validar

        Returns:
            True se o campo e autorizado, False caso contrario
        """
        return cls.sanitize_field_name(field_name) is not None

    @classmethod
    def attribute_to_key_map(cls) -> Dict[str, str]:
        return {field.attribute: key for key, field in cls.all_fields().items()}

    @classmethod
    def get_field(cls, key: str) -> Optional[Field]:
        return cls.all_fields().get(cls.resolve_key(key))

    @classmethod
    def get_attribute(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        field = cls.get_field(key)
        if field is None:
            return default
        return field.attribute

    @classmethod
    def resolve_key(cls, key_or_attribute: str) -> str:
        if not key_or_attribute:
            return key_or_attribute

        if key_or_attribute in cls.all_fields():
            return key_or_attribute

        if key_or_attribute in cls.attribute_to_key_map():
            return cls.attribute_to_key_map()[key_or_attribute]

        candidate = cls._to_pascal_case(key_or_attribute)
        if candidate in cls.all_fields():
            return candidate

        return key_or_attribute

    @classmethod
    def resolve_candidates(cls, key_or_attribute: str) -> List[str]:
        """
        Retorna lista ordenada de candidatos de chave canonica para lookup robusto.

        Suporta:
        - chave canonica (ex.: `SizeMb`)
        - attribute (ex.: `SizeMB`)
        - formatos com namespace/prefixo (ex.: `EXIF:SizeMb`, `xmp_bloco_1:drone-dji:GpsLatitude`)
        - variantes normalizadas em snake_case/PascalCase.
        """
        if not key_or_attribute:
            return []

        raw = str(key_or_attribute).strip()
        if not raw:
            return []

        seen = set()
        out: List[str] = []

        def _push(value: str):
            if value and value not in seen:
                seen.add(value)
                out.append(value)

        _push(raw)
        _push(cls.resolve_key(raw))

        # Se vier com namespace (EXIF:, MRK:, xmp_bloco_1:drone-dji:...), tenta sufixos.
        parts = [p for p in raw.split(":") if p]
        if len(parts) > 1:
            tail = parts[-1]
            _push(tail)
            _push(cls.resolve_key(tail))

        # Variantes por estilo de nome (snake -> Pascal etc.)
        pascal = cls._to_pascal_case(raw)
        _push(pascal)
        _push(cls.resolve_key(pascal))

        if len(parts) > 1:
            tail_pascal = cls._to_pascal_case(parts[-1])
            _push(tail_pascal)
            _push(cls.resolve_key(tail_pascal))

        # Mantem apenas candidatos que realmente existem no catalogo.
        catalog = cls.all_fields()
        return [candidate for candidate in out if candidate in catalog]

    @classmethod
    def resolve_output_name(cls, key_or_attribute: str) -> str:
        if not key_or_attribute:
            return key_or_attribute

        resolved_key = cls.resolve_key(key_or_attribute)
        if resolved_key in cls.all_fields():
            return cls.all_fields()[resolved_key].attribute

        if key_or_attribute in cls.attribute_to_key_map():
            return key_or_attribute

        return key_or_attribute

    @classmethod
    def resolve_output_names(cls, names: Iterable[str]) -> List[str]:
        resolved = [cls.resolve_output_name(name) for name in (names or [])]
        return StringAdapter.unique_preserve_order(resolved)

    @classmethod
    def normalize_selected_keys(
        cls,
        names: Iterable[str],
        *,
        allowed_keys: Optional[Iterable[str]] = None,
    ) -> List[str]:
        normalized = [cls.resolve_key(name) for name in (names or [])]
        normalized = StringAdapter.unique_preserve_order(normalized)
        if allowed_keys is None:
            return StringAdapter.filter_known_keys(normalized, cls.all_fields())

        allowed_set = set(allowed_keys)
        return [name for name in normalized if name in allowed_set]

    @classmethod
    def normalize_record_to_keys(cls, record: Dict[str, object]) -> Dict[str, object]:
        """
        Converte um registro com nomes de atributos de camada para chaves internas de metadata.
        Campos nao catalogados sao mantidos inalterados.
        """
        normalized = {}
        for key, value in (record or {}).items():
            candidates = cls.resolve_candidates(key)
            target_key = candidates[0] if candidates else cls.resolve_key(key)

            if target_key not in normalized:
                normalized[target_key] = value
                continue

            current_value = normalized.get(target_key)
            current_empty = current_value in (None, "")
            new_empty = value in (None, "")

            # Nao sobrescrever valor preenchido por valor vazio.
            if current_empty and (not new_empty):
                normalized[target_key] = value
        return normalized

    @classmethod
    def map_record_to_output_attributes(
        cls,
        record: Dict[str, object],
        *,
        exclude_keys: Optional[Iterable[str]] = None,
    ) -> Dict[str, object]:
        """
        Converte um registro baseado em chaves internas para nomes de atributos finais.
        """
        excluded = set(exclude_keys or [])
        mapped = {}
        for key, value in (record or {}).items():
            if key in excluded:
                continue
            mapped[cls.resolve_output_name(key)] = value
        return mapped

    @classmethod
    def default_track_attribute_keys(cls) -> List[str]:
        """
        Chaves canonicas para atributos da camada de trilha.
        """
        return [
            "DateName",
            "FolderLevel1",
            "FolderLevel2",
            "MrkFile",
            "MrkPath",
            "FlightNumber",
            "FlightName",
        ]
