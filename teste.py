#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gera_bbox_fotos_drone.py

Gera o footprint (bounding box REAL no terreno, considerando a rotação do
gimbal) de cada foto de um voo de drone (DJI RTK) a partir do JSON de
metadados (EXIF + MRK + XMP).

USO:
    python gera_bbox_fotos_drone.py entrada.json saida.geojson --keep 0.7

O resultado é um GeoJSON (EPSG:4326 / WGS84) que pode ser aberto direto no
QGIS (Camada > Adicionar Camada > Adicionar Camada Vetorial).

--------------------------------------------------------------------------
PARÂMETRO --keep (default 0.7)
--------------------------------------------------------------------------
keep=0.7 significa: mantém 70% da foto a partir do centro e corta 30% das
bordas (15% de cada lado, tanto na horizontal quanto na vertical). Isso é
feito reduzindo o meio-ângulo de visada (FOV) usado para projetar os 4
cantos da imagem no chão -- ou seja, o corte acontece no próprio cone de
visada da câmera, não apenas "encolhendo" o polígono final. Isso é
importante porque, em fotos oblíquas, encolher o polígono final por um
fator fixo não reproduz corretamente a perspectiva.

--------------------------------------------------------------------------
METODOLOGIA
--------------------------------------------------------------------------
1) FOV real da câmera:
   - Usa o campo LensSpecification (distância focal equivalente a 35mm,
     ex: 24mm) e o "frame" padrão de 36x24mm para calcular o meio-ângulo
     horizontal e vertical de visada:
         alpha_w = atan((18mm * keep) / focal35)
         alpha_h = atan((12mm * keep) / focal35)
   - Caso LensSpecification não exista, usa FocalLength real (mm) com um
     fator de crop aproximado (1.95, típico do sensor RGB do Zenmuse L2).

2) Orientação da câmera (gimbal):
   - Usa GimbalYawDegree / GimbalPitchDegree / GimbalRollDegree para montar
     uma matriz de rotação do referencial do corpo da câmera (NED: X=frente
     quando ângulos=0 (Norte), Y=direita (Leste), Z=baixo) para o mundo:
         R = Rz(yaw) * Ry(pitch) * Rx(roll)
   - Pitch = -90° => câmera olhando exatamente para baixo (nadir).
   - Pitch != -90° => câmera oblíqua: o footprint sai projetado para a
     frente/lado e NÃO fica centrado sob as coordenadas GPS da foto --
     exatamente o comportamento físico correto que você pediu.

3) Projeção no terreno:
   - Para cada um dos 4 cantos da imagem (já com o corte de --keep
     aplicado), cria-se um raio 3D partindo da câmera.
   - O raio é interceptado com o plano do terreno assumido em
     (altura relativa da câmera acima do solo) = campo RelativeAltitude do
     JSON (altura acima do ponto de decolagem/solo, mais confiável que a
     altitude absoluta/MSL para essa projeção).
   - O ponto de interseção (em metros, referencial local ENU) é convertido
     de volta para lat/lon.

4) Fotos nadir (pitch ~ -90°, tolerância 3°) resultam em um retângulo quase
   simétrico centrado sob a câmera. Fotos claramente oblíquas resultam em
   um trapézio deslocado -- o campo "is_nadir" em cada feature do GeoJSON
   informa qual foi o caso.

--------------------------------------------------------------------------
LIMITAÇÕES (importante ter em mente)
--------------------------------------------------------------------------
- Assume terreno plano (sem MDT/DEM) na altura definida por
  RelativeAltitude. Se o terreno tiver relevo significativo, o footprint
  real terá alguma distorção adicional não capturada aqui.
- Não é um cálculo fotogramétrico de precisão (não usa os coeficientes de
  distorção de lente Dewarp*); é uma estimativa geométrica de cone de
  visada, adequada para conferência de cobertura/sobreposição no QGIS.
- Fotos em que o raio de canto não intercepta o plano do terreno (ex.:
  câmera apontando para o horizonte) são descartadas e reportadas no
  resumo final.
"""

import json
import math
import argparse
import os

# --------------------------------------------------------------------------
# CONFIGURAÇÃO FIXA -- ajuste aqui se o caminho do JSON mudar.
# Assim o script roda sem precisar passar nada na linha de comando.
# --------------------------------------------------------------------------
JSON_IN_PADRAO = r"C:\Users\LINES-~1\AppData\Local\Temp\cadmus\reports\json\DPM_DJI_202608070833_001_AREA03_449pts_20260810_141953.json"
GEOJSON_OUT_PADRAO = None  # None = gera automaticamente ao lado do JSON de entrada (mesmo nome + .geojson)
KEEP_PADRAO = 0.7


def m_to_deg_lat(m):
    return m / 111320.0


def m_to_deg_lon(m, lat_deg):
    return m / (111320.0 * math.cos(math.radians(lat_deg)))


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def matmul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def matvec(A, v):
    return [sum(A[i][k] * v[k] for k in range(3)) for i in range(3)]


def gimbal_rotation_matrix(yaw_deg, pitch_deg, roll_deg):
    """Corpo (NED: X=frente/Norte, Y=direita/Leste, Z=baixo) -> Mundo (NED)."""
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)
    return matmul(rot_z(yaw), matmul(rot_y(pitch), rot_x(roll)))


def ned_to_enu(v_ned):
    n, e, d = v_ned
    return (e, n, -d)  # (E, N, U)


def compute_footprint(lat, lon, height_agl, yaw_deg, pitch_deg, roll_deg,
                       focal35_mm, keep_fraction=0.7):
    """Retorna lista de 4 pontos (lon,lat) -> footprint real no chão."""
    if height_agl is None or height_agl <= 0 or focal35_mm is None or focal35_mm <= 0:
        return None

    half_w_mm = 18.0 * keep_fraction  # metade de 36mm (frame equiv. 35mm)
    half_h_mm = 12.0 * keep_fraction  # metade de 24mm

    alpha_w = math.atan(half_w_mm / focal35_mm)
    alpha_h = math.atan(half_h_mm / focal35_mm)

    R = gimbal_rotation_matrix(yaw_deg, pitch_deg, roll_deg)

    # ordem dos cantos: TL, TR, BR, BL
    signs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]

    ground_pts = []
    for sw, sh in signs:
        theta_w = sw * alpha_w
        theta_h = sh * alpha_h
        v_body = [1.0, math.tan(theta_w), math.tan(theta_h)]  # frente, direita, baixo
        v_ned = matvec(R, v_body)
        dE, dN, dU = ned_to_enu(v_ned)

        if dU >= -1e-6:
            return None  # raio não atinge o solo (ex: aponta p/ horizonte)

        t = -height_agl / dU
        ground_E = dE * t
        ground_N = dN * t

        dlat = m_to_deg_lat(ground_N)
        dlon = m_to_deg_lon(ground_E, lat)
        ground_pts.append((lon + dlon, lat + dlat))

    return ground_pts


def get_focal35(rec):
    lens = rec.get("LensSpecification")
    if lens and len(lens) >= 1:
        try:
            return float(lens[0])
        except (TypeError, ValueError):
            pass
    focal_real = rec.get("FocalLength")
    if focal_real:
        try:
            return float(focal_real) * 1.95  # crop factor aproximado (Zenmuse L2 RGB)
        except (TypeError, ValueError):
            pass
    return None


def get_height_agl(rec):
    h = rec.get("RelativeAltitude")
    if h is not None:
        try:
            return float(h)
        except (TypeError, ValueError):
            pass
    return None


def process(json_path, out_path, keep_fraction, only_ok=True):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    groups = data.get("groups", {})
    features = []
    skipped = 0
    total = 0

    for group_name, group in groups.items():
        records = group.get("records", {})
        for fname, rec in records.items():
            total += 1

            if only_ok and rec.get("QualityFlag") != "OK":
                skipped += 1
                continue
            if not rec.get("HasExifGps", False):
                skipped += 1
                continue

            lat = rec.get("Lat", rec.get("GpsLatitude"))
            lon = rec.get("Lon", rec.get("GpsLongitude"))
            if lat is None or lon is None:
                skipped += 1
                continue

            yaw = rec.get("GimbalYawDegree")
            pitch = rec.get("GimbalPitchDegree")
            roll = rec.get("GimbalRollDegree")
            if yaw is None or pitch is None or roll is None:
                skipped += 1
                continue

            focal35 = get_focal35(rec)
            height_agl = get_height_agl(rec)

            if not focal35 or not height_agl:
                skipped += 1
                continue

            poly = compute_footprint(
                lat, lon, height_agl, yaw, pitch, roll, focal35, keep_fraction
            )
            if poly is None:
                skipped += 1
                continue

            ring = poly + [poly[0]]
            is_nadir = abs(pitch - (-90.0)) <= 3.0

            feature = {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {
                    "file": fname,
                    "flight": rec.get("FlightName"),
                    "flight_num": rec.get("FlightNumber"),
                    "datetime": rec.get("DateTimeOriginal"),
                    "cam_lat": lat,
                    "cam_lon": lon,
                    "height_agl_m": height_agl,
                    "gimbal_yaw": yaw,
                    "gimbal_pitch": pitch,
                    "gimbal_roll": roll,
                    "is_nadir": is_nadir,
                    "keep_fraction": keep_fraction,
                    "img_w": rec.get("ExifImageWidth"),
                    "img_h": rec.get("ExifImageHeight"),
                    "focal35_mm": focal35,
                },
            }
            features.append(feature)

    fc = {
        "type": "FeatureCollection",
        "name": "footprints_fotos_drone",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)

    print(f"Total de fotos no JSON: {total}")
    print(f"Footprints gerados:     {len(features)}")
    print(f"Fotos ignoradas:        {skipped}")
    print(f"Arquivo gerado:         {out_path}")


def main():
    ap = argparse.ArgumentParser(
        description="Gera footprints (bbox reais, com rotação de gimbal) das fotos de drone em GeoJSON, para uso no QGIS."
    )
    ap.add_argument(
        "json_in", nargs="?", default=JSON_IN_PADRAO,
        help=f"Caminho do JSON de metadados das fotos (default: {JSON_IN_PADRAO})",
    )
    ap.add_argument(
        "geojson_out", nargs="?", default=GEOJSON_OUT_PADRAO,
        help="Caminho do GeoJSON de saída (default: mesmo nome/pasta do JSON de entrada, com extensão .geojson)",
    )
    ap.add_argument(
        "--keep", type=float, default=KEEP_PADRAO,
        help=f"Fração da foto a manter, do centro para a borda (default {KEEP_PADRAO} = mantém {int(KEEP_PADRAO*100)}%%, corta {int((1-KEEP_PADRAO)*100)}%% da borda)",
    )
    ap.add_argument(
        "--all", action="store_true",
        help="Processa mesmo fotos com QualityFlag != OK",
    )
    args = ap.parse_args()

    geojson_out = args.geojson_out
    if not geojson_out:
        base, _ = os.path.splitext(args.json_in)
        geojson_out = base + "_footprints.geojson"

    process(args.json_in, geojson_out, args.keep, only_ok=not args.all)


if __name__ == "__main__":
    main()