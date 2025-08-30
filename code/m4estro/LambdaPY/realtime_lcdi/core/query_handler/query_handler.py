from typing import Optional, List
from sqlalchemy import func
from sqlalchemy.orm import Session

from model.alpha import Alpha
from model.alpha_opt import AlphaOpt
from model.order import Order
from model.site import Site
from model.carrier import Carrier
from model.manufacturer import Manufacturer
from model.shipment_time_gamma import ShipmentTimeGamma
from model.shipment_time_sample import ShipmentTimeSample
from model.shipment_time import ShipmentTime
from model.dispatch_time_gamma import DispatchTimeGamma
from model.dispatch_time_sample import DispatchTimeSample
from model.dispatch_time import DispatchTime
from model.estimated_time import EstimatedTime
from model.estimated_time_holiday import EstimatedTimeHoliday
from model.tmi import TMI
from model.wmi import WMI
from model.time_deviation import TimeDeviation
from model.estimation_params import EstimationParams

from core.query_handler.params.params_result import RTEstimatorParams
from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO
from core.calculator.dt.dt_dto import DT_DTO
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO
from core.calculator.tfst.pt.pt_dto import PT_DTO
from core.calculator.tfst.tt.tt_dto import TT_DTO
from core.calculator.tfst.pt.tmi.tmi_dto import TMI_DTO
from core.calculator.tfst.pt.wmi.wmi_dto import WMI_DTO

from core.executor.executor import ExecutorResult
from core.calculator.dt.holiday.holiday_dto import HolidayResultDTO
from core.executor.tfst_executor import TFSTExecutorResult

from core.calculator.time_deviation.time_deviation_dto import TimeDeviationDTO

from core.query_handler.query_result import (
    ShipmentTimeResult, ShipmentTimeGammaResult, ShipmentTimeSampleResult,
    DispatchTimeResult, DispatchTimeGammaResult, DispatchTimeSampleResult
)

from logger import get_logger
logger = get_logger(__name__)

class QueryHandler:
    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def get_order(self, order_id: int) -> Order:
        try:
            order: Order = self.session.query(Order).filter(Order.id == order_id).one()
        except Exception:
            logger.exception(f"Error retrieving order with ID {order_id}")
            raise
        
        return order
    
    def get_site(self, site_id: int) -> 'Site':
        try:
            site: 'Site' = self.session.query(Site).filter(Site.id == site_id).one()
        except Exception:
            logger.exception(f"Error retrieving site with ID {site_id}")
            raise
        
        return site
    
    def get_carrier(self, carrier_id: int) -> 'Carrier':
        try:
            carrier: 'Carrier' = self.session.query(Carrier).filter(Carrier.id == carrier_id).one()
        except Exception:
            logger.exception(f"Error retrieving carrier with ID {carrier_id}")
            raise
        
        return carrier
    
    def get_carrier_by_name(self, carrier_name: str) -> 'Carrier':
        try:
            carrier: 'Carrier' = self.session.query(Carrier).filter(func.lower(Carrier.name) == carrier_name.lower()).one()
        except Exception:
            logger.exception(f"Error retrieving carrier with name {carrier_name}")
            raise
        
        return carrier
    
    def get_manufacturer(self) -> 'Manufacturer':
        try:
            manufacturer: 'Manufacturer' = self.session.query(Manufacturer).one()
        except Exception:
            logger.exception("Error retrieving manufacturer")
            raise
        
        return manufacturer

    def get_alpha_opt(self, site_id: int, carrier_id: int) -> AlphaOpt:
        try:
            alpha_opt: AlphaOpt = self.session.query(AlphaOpt).filter_by(
                site_id=site_id,
                carrier_id=carrier_id
            ).one()
        except Exception:
            logger.exception(f"Error retrieving alpha optimal parameters for site ID {site_id} and carrier ID {carrier_id}")
            raise

        return alpha_opt
    
    def get_delivery_time(self, site_id: int, carrier_id: int) -> ShipmentTimeResult:
        session: Session = self.session

        dt_gamma: Optional[ShipmentTimeGamma] = session.query(ShipmentTimeGamma).filter_by(
            site_id=site_id,
            carrier_id=carrier_id
        ).one_or_none()
        if dt_gamma:
            return ShipmentTimeGammaResult(dt_gamma=dt_gamma)

        dt_sample: Optional[ShipmentTimeSample] = session.query(ShipmentTimeSample).filter_by(
            site_id=site_id,
            carrier_id=carrier_id
        ).one_or_none()
        if dt_sample:
            dt_x: List[float] = [
                hours for (hours,) in session.query(ShipmentTime.hours).filter_by(
                    site_id=site_id,
                    carrier_id=carrier_id
                ).all()
            ]
            return ShipmentTimeSampleResult(dt_sample=dt_sample, dt_x=dt_x)

        logger.error(f"No delivery time data found for site ID {site_id} and carrier ID {carrier_id}")
        raise ValueError(f"No delivery time data found for site ID {site_id} and carrier ID {carrier_id}")
    
    def get_dispatch_time(self, site_id: int) -> DispatchTimeResult:
        session: Session = self.session

        dt_gamma: Optional[DispatchTimeGamma] = session.query(DispatchTimeGamma).filter_by(site_id=site_id).one_or_none()
        if dt_gamma:
            return DispatchTimeGammaResult(dt_gamma=dt_gamma)

        dt_sample: Optional[DispatchTimeSample] = session.query(DispatchTimeSample).filter_by(site_id=site_id).one_or_none()
        if dt_sample:
            dt_x: List[float] = [
                hours for (hours,) in session.query(DispatchTime.hours).filter_by(
                    site_id=site_id,
                ).all()
            ]
            return DispatchTimeSampleResult(dt_x=dt_x, dt_sample=dt_sample)

        logger.error(f"No dispatch time data found for site ID {site_id}")
        raise ValueError(f"No dispatch time data found for site ID {site_id}")
    
    def save_estimated_time(
        self,  
        order_id: int, 
        vertex_id: int,
        order_status: str,
        executor_result: ExecutorResult
    ) -> EstimatedTime:
        
        session: Session = self.session
        time_sequence: TimeSequenceDTO = executor_result.time_sequence        
        
        dt_result: DT_DTO = executor_result.dt
        tfst_executor_result: TFSTExecutorResult = executor_result.tfst_executor_result
        alpha_result: AlphaDTO = tfst_executor_result.alpha
        pt_result: PT_DTO = tfst_executor_result.pt
        tt_result: TT_DTO = tfst_executor_result.tt
        td_result: TimeDeviationDTO = executor_result.time_deviation
        
        rte_params: RTEstimatorParams = pt_result.params.rte_estimator_params
        
        alpha_record: Alpha = Alpha(
            type=alpha_result.type_,
            tt_weight=alpha_result.maybe_tt_weight,
            tau=alpha_result.maybe_tau,
            gamma=alpha_result.maybe_gamma,
            input=alpha_result.input,
            value=alpha_result.value,
        )
        session.add(alpha_record)

        td_record: TimeDeviation = TimeDeviation(
            dt_hours_lower=float(td_result.dt_td_lower),
            dt_hours_upper=float(td_result.dt_td_upper),
            st_hours_lower=float(td_result.st_td_lower),
            st_hours_upper=float(td_result.st_td_upper),
            dt_confidence=float(td_result.dt_confidence),
            st_confidence=float(td_result.st_confidence),
        )
        session.add(td_record)

        estimation_params: EstimationParams = EstimationParams(
            dt_confidence=dt_result.confidence,
            consider_closure_holidays=dt_result.remaining_holidays.consider_closure_holidays,
            consider_working_holidays=dt_result.remaining_holidays.consider_working_holidays,
            consider_weekends_holidays=dt_result.remaining_holidays.consider_weekends_holidays,
            rte_mape=rte_params.model_mape,
            use_rte_model=rte_params.use_model,
            use_traffic_service=pt_result.params.tmi_params.use_traffic_service,
            tmi_max_timediff_hours=pt_result.params.tmi_params.traffic_max_timedelta,
            use_weather_service=pt_result.params.wmi_params.use_weather_service,
            wmi_max_timediff_hours=pt_result.params.wmi_params.weather_max_timedelta,
            wmi_step_distance_km=pt_result.params.wmi_params.step_distance_km,
            wmi_max_points=pt_result.params.wmi_params.max_points,
            pt_path_min_prob=pt_result.params.path_min_probability,
            pt_max_paths=pt_result.params.max_paths,
            pt_ext_data_min_prob=pt_result.params.ext_data_min_probability,
            pt_confidence=pt_result.params.confidence,
            tt_confidence=tt_result.confidence,
            tfst_tolerance=tfst_executor_result.tfst.tolerance,
        )
        session.add(estimation_params)
        session.flush()

        holiday_result: HolidayResultDTO = dt_result.total_holidays

        estimated_time: EstimatedTime = EstimatedTime(
            vertex_id=vertex_id,
            order_id=order_id,
            shipment_time=time_sequence.shipment_time,
            event_time=time_sequence.event_time,
            estimation_time=time_sequence.estimation_time,
            status=order_status,
            DT_weekend_days=len(holiday_result.weekend_holidays),
            DT=float(dt_result.total_time),
            DT_lower=float(dt_result.total_time_lower),
            DT_upper=float(dt_result.total_time_upper),
            PT_n_paths=pt_result.n_paths,
            PT_avg_tmi=float(pt_result.avg_tmi),
            PT_avg_wmi=float(pt_result.avg_wmi),
            TT_lower=float(tt_result.lower),
            TT_upper=float(tt_result.upper),
            PT_lower=float(pt_result.lower),
            PT_upper=float(pt_result.upper),
            TFST_lower=float(tfst_executor_result.tfst.lower),
            TFST_upper=float(tfst_executor_result.tfst.upper),
            EST=float(executor_result.est.value),
            EODT=float(executor_result.eodt.value),
            CFDI_lower=float(executor_result.cfdi.lower),
            CFDI_upper=float(executor_result.cfdi.upper),
            EDD=executor_result.edd.value,
            time_deviation_id=td_record.id,
            alpha_id=alpha_record.id,
            estimation_params_id=estimation_params.id,
        )
        session.add(estimated_time)
        session.flush()

        for h_list in (holiday_result.closure_holidays, holiday_result.working_holidays): 
            for h in h_list:  
                eth: EstimatedTimeHoliday = EstimatedTimeHoliday(
                    estimated_time_id=estimated_time.id,
                    holiday_id=h.id
                )
                session.add(eth)

        tmi_data: List[TMI_DTO] = pt_result.tmi_data
        for tmi_dto in tmi_data:
            tmi: TMI = TMI(
                estimated_time_id=estimated_time.id,
                source_id=tmi_dto.source_id,
                destination_id=tmi_dto.destination_id,
                timestamp=tmi_dto.timestamp,
                transportation_mode=tmi_dto.transportation_mode,
                value=tmi_dto.value
            )
            session.add(tmi)

        wmi_data: List[WMI_DTO] = pt_result.wmi_data
        for wmi_dto in wmi_data:
            wmi: WMI = WMI(
                estimated_time_id=estimated_time.id,
                source_id=wmi_dto.source_id,
                destination_id=wmi_dto.destination_id,
                timestamp=wmi_dto.timestamp,
                n_interpolation_points=wmi_dto.n_interpolation_points,
                step_distance_km=wmi_dto.step_distance_km,
                value=wmi_dto.value
            )
            session.add(wmi)

        session.commit()

        return estimated_time