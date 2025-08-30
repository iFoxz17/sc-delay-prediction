from typing import Dict, Tuple, List, Any
from sqlalchemy.orm import Session

from model.alpha import AlphaType
from model.param import Param, ParamName, ParamGeneralCategory

from core.query_handler.params.params_result import (
    DTParams,
    HolidayParams,
    TFSTParams,
    AlphaParams,
    TMIParams, TMISpeedParameters, TMIDistanceParameters,
    WMIParams,
    PTParams,
    TTParams,
    RTEstimatorParams,
    TimeDeviationParams,
    ParamsResult,
)

from logger import get_logger
logger = get_logger(__name__)

class ParamsHandler:
    def __init__(self, session: Session, default_alpha_type: AlphaType = AlphaType.CONST):
        self.session: Session = session
        self.default_alpha_type: AlphaType = default_alpha_type

    def get_params(self) -> ParamsResult:
        try:
            realtime_params_map: Dict[str, float] = self._get_param_values_by_general_category(ParamGeneralCategory.REALTIME)

            dt_params: DTParams = self._get_dt_params(realtime_params_map)
            tfst_params: TFSTParams = self._get_tfst_params(realtime_params_map)
            time_deviation_params: TimeDeviationParams = self._get_time_deviation_params(realtime_params_map)

            system_params_map: Dict[str, float] = self._get_param_values_by_general_category(ParamGeneralCategory.SYSTEM)
            parallelization: int = int(system_params_map[ParamName.PARALLELIZATION.value])

            return ParamsResult(
                dt_params=dt_params,
                tfst_params=tfst_params,
                time_deviation_params=time_deviation_params,
                parallelization=parallelization,
            )
        except Exception:
            logger.exception("Error retrieving parameters")
            raise

    def _get_param_values_by_general_category(self, general_category: ParamGeneralCategory) -> Dict[str, float]:
        rows: List[Any] = (
            self.session.query(Param.name, Param.value)
            .filter(Param.general_category == general_category.value)
            .all()
        )
        return {name: value for name, value in rows}

    def _get_dt_params(self, values: Dict[str, float]) -> DTParams:
        holiday_params: HolidayParams = HolidayParams(
            consider_closure_holidays=bool(int(values[ParamName.CONSIDER_CLOSURE_HOLIDAYS.value])),
            consider_working_holidays=bool(int(values[ParamName.CONSIDER_WORKING_HOLIDAYS.value])),
            consider_weekends_holidays=bool(int(values[ParamName.CONSIDER_WEEKENDS_HOLIDAYS.value])),
        )
        confidence: float = float(values[ParamName.DT_CONFIDENCE.value])
        return DTParams(holidays_params=holiday_params, confidence=confidence)

    def _get_tfst_params(self, values: Dict[str, float]) -> TFSTParams:
        try:
            alpha_type: AlphaType = AlphaType.from_code(int(values[ParamName.ALPHA_CALCULATOR_TYPE.value]))
        except (KeyError, ValueError, TypeError):
            logger.warning("Invalid or missing alpha calculator type; using default.")
            alpha_type: AlphaType = self.default_alpha_type

        alpha_params: AlphaParams = AlphaParams(
            const_alpha_value=float(values[ParamName.ALPHA_CONST_VALUE.value]),
            alpha_type=alpha_type
        )

        pt_params: PTParams = PTParams(
            rte_estimator_params=self._get_rt_estimator_params(values),
            tmi_params=self._get_tmi_params(values),
            wmi_params=self._get_wmi_params(values),
            path_min_probability=float(values[ParamName.PT_PATH_MIN_PROBABILITY.value]),
            max_paths=int(values[ParamName.PT_MAX_PATHS.value]),
            ext_data_min_probability=float(values[ParamName.PT_EXT_DATA_MIN_PROBABILITY.value]),
            confidence=float(values[ParamName.PT_CONFIDENCE.value]),
        )

        tt_params: TTParams = TTParams(
            confidence=float(values[ParamName.TT_CONFIDENCE.value])
        )

        return TFSTParams(
            alpha_params=alpha_params,
            pt_params=pt_params,
            tt_params=tt_params,
            tolerance=float(values[ParamName.TFST_TOLERANCE.value])
        )

    def _get_time_deviation_params(self, values: Dict[str, float]) -> TimeDeviationParams:
        return TimeDeviationParams(
            dt_time_deviation_confidence=float(values[ParamName.DELAY_DT_CONFIDENCE.value]),
            st_time_deviation_confidence=float(values[ParamName.DELAY_ST_CONFIDENCE.value]),
        )

    def _get_rt_estimator_params(self, values: Dict[str, float]) -> RTEstimatorParams:
        return RTEstimatorParams(
            model_mape=float(values[ParamName.RT_ESTIMATOR_MODEL_MAPE.value]),
            use_model=bool(int(values[ParamName.RT_ESTIMATOR_USE_MODEL.value])),
        )

    def _get_tmi_params(self, values: Dict[str, float]) -> TMIParams:
        tmi_speed_params: TMISpeedParameters = TMISpeedParameters(
            air_min_speed_km_h=float(values[ParamName.TMI_AIR_MIN_SPEED_KM_H.value]),
            air_max_speed_km_h=float(values[ParamName.TMI_AIR_MAX_SPEED_KM_H.value]),
            sea_min_speed_km_h=float(values[ParamName.TMI_SEA_MIN_SPEED_KM_H.value]),
            sea_max_speed_km_h=float(values[ParamName.TMI_SEA_MAX_SPEED_KM_H.value]),
            rail_min_speed_km_h=float(values[ParamName.TMI_RAIL_MIN_SPEED_KM_H.value]),
            rail_max_speed_km_h=float(values[ParamName.TMI_RAIL_MAX_SPEED_KM_H.value]),
            road_min_speed_km_h=float(values[ParamName.TMI_ROAD_MIN_SPEED_KM_H.value]),
            road_max_speed_km_h=float(values[ParamName.TMI_ROAD_MAX_SPEED_KM_H.value]),
        )

        tmi_distance_params: TMIDistanceParameters = TMIDistanceParameters(
            air_min_distance_km=float(values[ParamName.TMI_AIR_MIN_DISTANCE_KM.value]),
            air_max_distance_km=float(values[ParamName.TMI_AIR_MAX_DISTANCE_KM.value]),
            sea_min_distance_km=float(values[ParamName.TMI_SEA_MIN_DISTANCE_KM.value]),
            sea_max_distance_km=float(values[ParamName.TMI_SEA_MAX_DISTANCE_KM.value]),
            rail_min_distance_km=float(values[ParamName.TMI_RAIL_MIN_DISTANCE_KM.value]),
            rail_max_distance_km=float(values[ParamName.TMI_RAIL_MAX_DISTANCE_KM.value]),
            road_min_distance_km=float(values[ParamName.TMI_ROAD_MIN_DISTANCE_KM.value]),
            road_max_distance_km=float(values[ParamName.TMI_ROAD_MAX_DISTANCE_KM.value]),
        )

        return TMIParams(
            speed_parameters=tmi_speed_params,
            distance_parameters=tmi_distance_params,
            use_traffic_service=bool(int(values[ParamName.TMI_USE_TRAFFIC_SERVICE.value])),
            traffic_max_timedelta=float(values[ParamName.TMI_TRAFFIC_MAX_TIMEDIFF.value]),
        )

    def _get_wmi_params(self, values: Dict[str, float]) -> WMIParams:
        return WMIParams(
            use_weather_service=bool(int(values[ParamName.WMI_USE_WEATHER_SERVICE.value])),
            weather_max_timedelta=float(values[ParamName.WMI_WEATHER_MAX_TIMEDIFF.value]),
            step_distance_km=float(values[ParamName.WMI_STEP_DISTANCE_KM.value]),
            max_points=int(values[ParamName.WMI_MAX_POINTS.value]),
        )
