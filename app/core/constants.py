# -*- coding: utf-8 -*-
from enum import Enum
from pydantic import BaseModel

class PathState(str, Enum):
    LOCKED = "LOCKED"
    AVAILABLE = "AVAILABLE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class MasteryLevel(str, Enum):
    WEAK = "薄弱"
    DEVELOPING = "发展中"
    MASTERED = "已掌握"

class BKTParameters(BaseModel):
    p_init: float = 0.20
    p_transit: float = 0.10
    p_guess: float = 0.20
    p_slip: float = 0.10

DEFAULT_BKT_PARAMS = BKTParameters()
MASTERY_THRESHOLD_HIGH = 0.80
MASTERY_THRESHOLD_LOW = 0.60
DEMOTION_THRESHOLD = 0.70
