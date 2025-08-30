from enum import Enum

from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from model.base import Base

class ParamGeneralCategory(Enum):
    HISTORICAL = 'HISTORICAL'
    REALTIME = 'REALTIME'
    SYSTEM = 'SYSTEM'

class ParamCategory(Enum):
    DISPATCH_TIME = 'DISPATCH_TIME'
    SHIPMENT_TIME = 'SHIPMENT_TIME'
    HOLIDAY = 'HOLIDAY'
    ALPHA = 'ALPHA'
    TMI = 'TMI'
    WMI = 'WMI'
    ROUTE_TIME_ESTIMATOR = 'ROUTE_TIME_ESTIMATOR'
    PT = 'PT'
    TT = 'TT'
    TFST = 'TFST'
    SYSTEM = 'SYSTEM'

class ParamName(Enum):
    # Historical indicators parameters
    DISPATCH_HIST_CONFIDENCE = 'HISTORICAL_DISPATCH_CONFIDENCE'
    SHIPMENT_HIST_CONFIDENCE = 'HISTORICAL_SHIPMENT_CONFIDENCE'

    # DT parameters
    DT_CONFIDENCE = 'DT_CONFIDENCE'
    # Holiday parameters
    CONSIDER_CLOSURE_HOLIDAYS = 'DISPATCH_CLOSURE_HOLIDAYS'
    CONSIDER_WORKING_HOLIDAYS = 'DISPATCH_WORKING_HOLIDAYS'
    CONSIDER_WEEKENDS_HOLIDAYS = 'DISPATCH_CLOSURE_WEEKENDS'

    
    # TMI parameters
    # TMI calculator speed parameters
    TMI_AIR_MIN_SPEED_KM_H = 'TMI_AIR_MIN_SPEED_KM_H'
    TMI_AIR_MAX_SPEED_KM_H = 'TMI_AIR_MAX_SPEED_KM_H'
    TMI_SEA_MIN_SPEED_KM_H = 'TMI_SEA_MIN_SPEED_KM_H'
    TMI_SEA_MAX_SPEED_KM_H = 'TMI_SEA_MAX_SPEED_KM_H'
    TMI_RAIL_MIN_SPEED_KM_H = 'TMI_RAIL_MIN_SPEED_KM_H'
    TMI_RAIL_MAX_SPEED_KM_H = 'TMI_RAIL_MAX_SPEED_KM_H'
    TMI_ROAD_MIN_SPEED_KM_H = 'TMI_ROAD_MIN_SPEED_KM_H'
    TMI_ROAD_MAX_SPEED_KM_H = 'TMI_ROAD_MAX_SPEED_KM_H'
    # TMI calculator distance parameters
    TMI_AIR_MIN_DISTANCE_KM = 'TMI_AIR_MIN_DISTANCE_KM'
    TMI_AIR_MAX_DISTANCE_KM = 'TMI_AIR_MAX_DISTANCE_KM'
    TMI_SEA_MIN_DISTANCE_KM = 'TMI_SEA_MIN_DISTANCE_KM'
    TMI_SEA_MAX_DISTANCE_KM = 'TMI_SEA_MAX_DISTANCE_KM'
    TMI_RAIL_MIN_DISTANCE_KM = 'TMI_RAIL_MIN_DISTANCE_KM'
    TMI_RAIL_MAX_DISTANCE_KM = 'TMI_RAIL_MAX_DISTANCE_KM'
    TMI_ROAD_MIN_DISTANCE_KM = 'TMI_ROAD_MIN_DISTANCE_KM'
    TMI_ROAD_MAX_DISTANCE_KM = 'TMI_ROAD_MAX_DISTANCE_KM'
    # TMI management parameters
    TMI_USE_TRAFFIC_SERVICE = 'TMI_USE_TRAFFIC_SERVICE'
    TMI_TRAFFIC_MAX_TIMEDIFF = 'TMI_TRAFFIC_MAX_TIMEDIFF'

    # WMI parameters
    WMI_USE_WEATHER_SERVICE = 'WMI_USE_WEATHER_SERVICE'
    WMI_WEATHER_MAX_TIMEDIFF = 'WMI_WEATHER_MAX_TIMEDIFF'
    WMI_STEP_DISTANCE_KM = 'WMI_STEP_DISTANCE_KM'
    WMI_MAX_POINTS = 'WMI_MAX_POINTS'
    
    # Route time estimator parameters
    RT_ESTIMATOR_MODEL_MAPE = 'RT_ESTIMATOR_MODEL_MAPE'
    RT_ESTIMATOR_USE_MODEL = 'USE_RT_ESTIMATOR_MODEL'

    # Alpha parameters
    ALPHA_CONST_VALUE = 'ALPHA_CONST_VALUE'
    ALPHA_CALCULATOR_TYPE = 'ALPHA_CALCULATOR_TYPE'

    # PT parameters
    PT_PATH_MIN_PROBABILITY = 'PT_PATH_MIN_PROBABILITY'
    PT_MAX_PATHS = 'PT_MAX_PATHS'
    PT_EXT_DATA_MIN_PROBABILITY = 'PT_EXT_DATA_MIN_PROBABILITY'
    PT_CONFIDENCE = 'PT_CONFIDENCE'

    # TT parameters
    TT_CONFIDENCE = 'TT_CONFIDENCE'

    # TFST parameters
    TFST_TOLERANCE = 'TFST_TOLERANCE'
    
    # Time deviation parameters
    DELAY_DT_CONFIDENCE = 'DELAY_DISPATCH_CONFIDENCE'
    DELAY_ST_CONFIDENCE = 'DELAY_SHIPMENT_CONFIDENCE'
    
    # System parameters
    PARALLELIZATION = 'PARALLELIZATION'

PARAM_TABLE_NAME = 'params'

class Param(Base):
    __tablename__ = PARAM_TABLE_NAME
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    general_category: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint('name', name='uq_param_name'),
    )

    def __str__(self) -> str:
        return (f"Param(id={self.id}, name={self.name}, "
                f"general_category={self.general_category}, category={self.category}, "
                f"description={self.description}, value={self.value})")