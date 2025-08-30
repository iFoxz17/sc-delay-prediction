from typing import Dict, Any
from dataclasses import dataclass

from model.alpha import AlphaType

from core.exception.invalid_tmi_parameters import InvalidTMIParameters

@dataclass(frozen=True)
class HolidayParams:
    consider_closure_holidays: bool
    consider_working_holidays: bool
    consider_weekends_holidays: bool

    def to_dict(self) -> Dict[str, bool]:
        return {
            'consider_closure_holidays': self.consider_closure_holidays,
            'consider_working_holidays': self.consider_working_holidays,
            'consider_weekends_holidays': self.consider_weekends_holidays
        }

@dataclass(frozen=True)
class DTParams:
    holidays_params: HolidayParams
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'holidays_params': self.holidays_params.to_dict(),
            'confidence': self.confidence
        }


@dataclass(frozen=True)
class AlphaParams:
    const_alpha_value: float
    alpha_type: AlphaType  

    def to_dict(self) -> Dict[str, Any]:
        return {
            'const_alpha_value': self.const_alpha_value,
            'alpha_type': self.alpha_type.value
        }


@dataclass(frozen=True)
class TMISpeedParameters:
    air_min_speed_km_h: float
    air_max_speed_km_h: float

    sea_min_speed_km_h: float
    sea_max_speed_km_h: float

    rail_min_speed_km_h: float
    rail_max_speed_km_h: float

    road_min_speed_km_h: float
    road_max_speed_km_h: float

    def __post_init__(self):
        if not 0 <= self.air_min_speed_km_h <= self.air_max_speed_km_h:
            raise InvalidTMIParameters(f"Invalid air speed parameters: air_min_speed = {self.air_min_speed_km_h}, air_max_speed = {self.air_max_speed_km_h}")
        if not 0 <= self.sea_min_speed_km_h <= self.sea_max_speed_km_h:
            raise InvalidTMIParameters(f"Invalid sea speed parameters: sea_min_speed = {self.sea_min_speed_km_h}, sea_max_speed = {self.sea_max_speed_km_h}")
        if not 0 <= self.rail_min_speed_km_h <= self.rail_max_speed_km_h:
            raise InvalidTMIParameters(f"Invalid rail speed parameters: rail_min_speed = {self.rail_min_speed_km_h}, rail_max_speed = {self.rail_max_speed_km_h}")
        if not 0 <= self.road_min_speed_km_h <= self.road_max_speed_km_h:
            raise InvalidTMIParameters(f"Invalid road speed parameters: road_min_speed = {self.road_min_speed_km_h}, road_max_speed = {self.road_max_speed_km_h}")

    @staticmethod
    def default():
        return TMISpeedParameters(
            air_min_speed_km_h=0.0,
            air_max_speed_km_h=0.0,
            sea_min_speed_km_h=0.0,
            sea_max_speed_km_h=0.0,
            rail_min_speed_km_h=0.0,
            rail_max_speed_km_h=0.0,
            road_min_speed_km_h=0.0,
            road_max_speed_km_h=0.0
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'air_min_speed_km_h': self.air_min_speed_km_h,
            'air_max_speed_km_h': self.air_max_speed_km_h,
            'sea_min_speed_km_h': self.sea_min_speed_km_h,
            'sea_max_speed_km_h': self.sea_max_speed_km_h,
            'rail_min_speed_km_h': self.rail_min_speed_km_h,
            'rail_max_speed_km_h': self.rail_max_speed_km_h,
            'road_min_speed_km_h': self.road_min_speed_km_h,
            'road_max_speed_km_h': self.road_max_speed_km_h
        }

@dataclass(frozen=True)
class TMIDistanceParameters:
    air_min_distance_km: float
    air_max_distance_km: float

    sea_min_distance_km: float
    sea_max_distance_km: float

    rail_min_distance_km: float
    rail_max_distance_km: float

    road_min_distance_km: float
    road_max_distance_km: float

    def __post_init__(self):
        if not 0 <= self.air_min_distance_km <= self.air_max_distance_km:
            raise InvalidTMIParameters(f"Invalid air distance parameters: air_min_distance = {self.air_min_distance_km}, air_max_distance = {self.air_max_distance_km}")
        if not 0 <= self.sea_min_distance_km <= self.sea_max_distance_km:
            raise InvalidTMIParameters(f"Invalid sea distance parameters: sea_min_distance = {self.sea_min_distance_km}, sea_max_distance = {self.sea_max_distance_km}")
        if not 0 <= self.rail_min_distance_km <= self.rail_max_distance_km:
            raise InvalidTMIParameters(f"Invalid rail distance parameters: rail_min_distance = {self.rail_min_distance_km}, rail_max_distance = {self.rail_max_distance_km}")
        if not 0 <= self.road_min_distance_km <= self.road_max_distance_km:
            raise InvalidTMIParameters(f"Invalid road distance parameters: road_min_distance = {self.road_min_distance_km}, road_max_distance = {self.road_max_distance_km}")

    @staticmethod
    def default():
        return TMIDistanceParameters(
            air_min_distance_km=0.0,
            air_max_distance_km=0.0,
            sea_min_distance_km=0.0,
            sea_max_distance_km=0.0,
            rail_min_distance_km=0.0,
            rail_max_distance_km=0.0,
            road_min_distance_km=0.0,
            road_max_distance_km=0.0
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'air_min_distance_km': self.air_min_distance_km,
            'air_max_distance_km': self.air_max_distance_km,
            'sea_min_distance_km': self.sea_min_distance_km,
            'sea_max_distance_km': self.sea_max_distance_km,
            'rail_min_distance_km': self.rail_min_distance_km,
            'rail_max_distance_km': self.rail_max_distance_km,
            'road_min_distance_km': self.road_min_distance_km,
            'road_max_distance_km': self.road_max_distance_km
        }

@dataclass(frozen=True)
class TMIParams:
    speed_parameters: TMISpeedParameters
    distance_parameters: TMIDistanceParameters
    use_traffic_service: bool
    traffic_max_timedelta: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'speed_parameters': self.speed_parameters.to_dict(),
            'distance_parameters': self.distance_parameters.to_dict(),
            'use_traffic_service': self.use_traffic_service,
            'traffic_max_timedelta': self.traffic_max_timedelta
        }

@dataclass(frozen=True)
class WMIParams:
    use_weather_service: bool
    weather_max_timedelta: float
    step_distance_km: float
    max_points: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'use_weather_service': self.use_weather_service,
            'weather_max_timedelta': self.weather_max_timedelta,
            'step_distance_km': self.step_distance_km,
            'max_points': self.max_points
        }

@dataclass(frozen=True)
class RTEstimatorParams:
    model_mape: float
    use_model: bool

    def to_dict(self) -> Dict[str, float]:
        return {
            'model_mape': self.model_mape,
            'use_model': self.use_model
        }

@dataclass(frozen=True)
class PTParams:
    rte_estimator_params: RTEstimatorParams
    tmi_params: TMIParams
    wmi_params: WMIParams
    path_min_probability: float
    max_paths: int
    ext_data_min_probability: float
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rte_estimator_params': self.rte_estimator_params.to_dict(),
            'tmi_params': self.tmi_params.to_dict(),
            'wmi_params': self.wmi_params.to_dict(),
            'path_min_probability': self.path_min_probability,
            'max_paths': self.max_paths,
            'ext_data_min_probability': self.ext_data_min_probability,
            'confidence': self.confidence
        }
    

@dataclass(frozen=True)
class TTParams:
    confidence: float

    def to_dict(self) -> Dict[str, float]:
        return {
            'confidence': self.confidence
        }


@dataclass(frozen=True)
class TFSTParams:
    alpha_params: AlphaParams
    pt_params: PTParams
    tt_params: TTParams
    tolerance: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'alpha_params': self.alpha_params.to_dict(),
            'pt_params': self.pt_params.to_dict(),
            'tt_params': self.tt_params.to_dict(),
            'tolerance': self.tolerance
        }


@dataclass(frozen=True)
class TimeDeviationParams:
    dt_time_deviation_confidence: float
    st_time_deviation_confidence: float

    def to_dict(self) -> Dict[str, float]:
        return {
            'dt_time_deviation_confidence': self.dt_time_deviation_confidence,
            'st_time_deviation_confidence': self.st_time_deviation_confidence
        }

    
@dataclass(frozen=True)
class ParamsResult:
    dt_params: DTParams
    tfst_params: TFSTParams
    time_deviation_params: TimeDeviationParams
    parallelization: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'dt_params': self.dt_params.to_dict(),
            'tfst_params': self.tfst_params.to_dict(),
            'time_deviation_params': self.time_deviation_params.to_dict(),
            'parallelization': self.parallelization
        }