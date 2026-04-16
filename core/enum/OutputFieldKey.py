# -*- coding: utf-8 -*-
from enum import Enum


class OutputFieldKey(Enum):
    # OUTPUT FIELDS FOR SEQUENTIAL POINT BREAK JUDGE
    SHOT_ID = "shot_id"
    SHOT_VALID = "shot_valid"
    SCORE = "score"
    SCORE_DIRECTION = "score_direction"
    SCORE_CONTINUITY = "score_continuity"
    SEG_TYPE = "seg_type"
    AZIMUTH_INSTANT = "azimuth_instant"
    AZIMUTH_MEAN = "azimuth_mean"
    DELTA_AZIMUTH = "delta_azimuth"
    DELTA_TIME = "delta_time"
    DELTA_DISTANCE = "delta_distance"
    VELOCITY_INSTANT = "velocity_instant"