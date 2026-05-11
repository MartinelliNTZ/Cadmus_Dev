# -*- coding: utf-8 -*-
import json
from typing import List, Dict, Any, Optional, Tuple

from qgis.core import QgsVectorLayer, QgsField, QgsPointXY
from qgis.PyQt.QtCore import QVariant

from ..config.LogUtils import LogUtils
from ..enum import MetadataFieldKey
from ...utils.mrk.MetadataFields import MetadataFields
from ...utils.vector.VectorLayerGeometry import VectorLayerGeometry


class JsonToVectorTranslator:
    """
    Traduz JSON canônico v2.0 para QgsVectorLayer.

    Para cada registro:
    - busca o Field em MetadataFields via field.key
    - usa field.attribute como nome do atributo no layer (máx 9 chars)
    - usa field.label para documentação interna

    Geometria:
    - source "mrk":        usa MetadataFieldKey.LAT / LON / ALT
    - source "mrk+photo":  usa MetadataFieldKey.GPS_LATITUDE / GPS_LONGITUDE / ABSOLUTE_ALTITUDE
    - source "photo_only": usa MetadataFieldKey.GPS_LATITUDE / GPS_LONGITUDE / ABSOLUTE_ALTITUDE
    - fallback:            qualquer campo de coordenada válido presente no registro
    """

    def __init__(self, tool_key: str = "json_translator"):
        self.tool_key = tool_key
        self.logger = LogUtils(tool=tool_key, class_name="JsonToVectorTranslator")

    def translate(
        self,
        json_path: str,
        layer_name: str,
        selected_keys: Optional[List[str]] = None,
        source: Optional[str] = None,
    ) -> QgsVectorLayer:
        """
        Lê o JSON v2.0, monta schema de campos, cria features com
        geometria Point e retorna o layer.
        Lança ValueError se schema_version != "2.0".
        """
        from ...utils.JsonUtil import JsonUtil

        # Carregar registros do JSON
        records = JsonUtil.load_records(json_path)

        if not records:
            raise ValueError(f"Nenhum registro encontrado no JSON: {json_path}")

        # Determinar source - usar parâmetro ou tentar ler do JSON
        if source is None:
            # Tentar ler source do JSON raiz
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                source = json_data.get("source", "unknown")
            except:
                source = "unknown"

        # Resolver geometria para todos os registros
        valid_records = []
        for record in records:
            geom = self._resolve_geometry(record, source)
            if geom:
                record["_geometry"] = geom
                valid_records.append(record)

        if not valid_records:
            raise ValueError(f"Nenhum registro com geometria válida encontrado")

        # Construir schema
        schema = self._build_schema(valid_records[0], selected_keys)

        # Preparar registros para VectorLayerGeometry
        points = []
        for record in valid_records:
            point_dict = {}
            geom = record.pop("_geometry")

            # Adicionar campos selecionados
            for key, value in record.items():
                if selected_keys is None or key in selected_keys:
                    # Resolver nome do atributo
                    attr_name = self._resolve_attribute_name(key)
                    point_dict[attr_name] = value

            # Adicionar coordenadas separadamente para geometria
            point_dict["_lon"] = geom.x()
            point_dict["_lat"] = geom.y()
            points.append(point_dict)

        # Criar layer
        layer = VectorLayerGeometry.create_point_layer_from_dicts(
            points=points,
            name=layer_name,
            field_specs=schema,
            geometry_keys=("_lon", "_lat"),
            tool_key=self.tool_key,
        )

        self.logger.info(
            f"Layer criado: {layer_name}",
            data={
                "total_records": len(records),
                "valid_records": len(valid_records),
                "schema_fields": len(schema),
                "source": source
            }
        )

        return layer

    def _build_schema(
        self,
        sample_record: Dict,
        selected_keys: Optional[List[str]],
    ) -> List[Tuple[str, QVariant, str]]:
        """
        Para cada chave do registro, busca o Field em MetadataFields
        e usa field.attribute como nome do QgsField.
        Chaves sem Field catalogado usam a própria chave truncada a 9 chars.
        """
        schema = []

        for key in sample_record.keys():
            if key.startswith("_") or key in ["source"]:  # Campos internos
                continue

            if selected_keys is not None and key not in selected_keys:
                continue

            # Resolver nome do atributo
            attr_name = self._resolve_attribute_name(key)

            # Determinar tipo QVariant
            value = sample_record[key]
            if isinstance(value, (int, float)):
                qtype = QVariant.Double
            elif isinstance(value, bool):
                qtype = QVariant.Bool
            else:
                qtype = QVariant.String

            schema.append((attr_name, qtype, attr_name))

        return schema

    def _resolve_geometry(self, record: Dict, source: str) -> Optional[QgsPointXY]:
        """
        Resolve coordenadas conforme source e CoordSource do registro.
        """
        try:
            if source == "mrk":
                lat = record.get(MetadataFieldKey.LAT.value)
                lon = record.get(MetadataFieldKey.LON.value)
            elif source in ["mrk+photo", "photo_only"]:
                lat = record.get(MetadataFieldKey.GPS_LATITUDE.value)
                lon = record.get(MetadataFieldKey.GPS_LONGITUDE.value)
            else:
                # Fallback: procurar qualquer campo de coordenada
                lat = record.get(MetadataFieldKey.GPS_LATITUDE.value) or record.get(MetadataFieldKey.LAT.value)
                lon = record.get(MetadataFieldKey.GPS_LONGITUDE.value) or record.get(MetadataFieldKey.LON.value)

            if lat is not None and lon is not None:
                return QgsPointXY(float(lon), float(lat))

        except (ValueError, TypeError):
            pass

        return None

    def _resolve_attribute_name(self, key: str) -> str:
        """
        Resolve o nome do atributo usando MetadataFields.
        """
        # Procurar field por key.value
        for field_key, field in MetadataFields.EXIF_FIELDS.items():
            if field_key.value == key and field.key:
                return field.attribute

        for field_key, field in MetadataFields.DJI_XMP_FIELDS.items():
            if field_key.value == key and field.key:
                return field.attribute

        for field_key, field in MetadataFields.CUSTOM_FIELDS.items():
            if field_key.value == key and field.key:
                return field.attribute

        for field_key, field in MetadataFields.MRK_FIELDS.items():
            if field_key.value == key and field.key:
                return field.attribute

        # Fallback: truncar chave a 9 caracteres
        return key[:9]