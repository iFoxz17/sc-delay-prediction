from typing import List, Optional
from datetime import datetime

from model.dispatch_time_gamma import DispatchTimeGamma
from model.dispatch_time_sample import DispatchTimeSample

from core.query_handler.query_result import DispatchTimeResult, DispatchTimeGammaResult, DispatchTimeSampleResult
from core.query_handler.query_result import ShipmentTimeResult, ShipmentTimeGammaResult, ShipmentTimeSampleResult

from core.calculator.dt.dt_input_dto import DTInputDTO, DTDistributionInputDTO, DTShipmentTimeInputDTO, DTDistributionDTO, DTGammaDTO, DTSampleDTO
from core.calculator.dt.dt_dto import DT_DTO
from core.calculator.tfst.alpha.alpha_input_dto import AlphaInputDTO, AlphaBaseInputDTO, AlphaGammaDTO, AlphaSampleDTO
from core.calculator.tfst.pt.pt_input_dto import PTInputDTO, PTBaseInputDTO
from core.calculator.tfst.tt.tt_input_dto import TTInputDTO, TTBaseInputDTO, TTGammaDTO, TTSampleDTO
from core.calculator.tfst.tfst_dto import TFST_DTO
from core.calculator.time_deviation.time_deviation_input_dto import TimeDeviationBaseInputDTO, TimeDeviationInputDTO, STDistributionDTO, STGammaDTO, STSampleDTO

class DTOFactory:
    def __init__(self) -> None:
        pass

    def _create_dt_distribution(self, dispatch_time_result: DispatchTimeResult) -> DTDistributionDTO:
        if isinstance(dispatch_time_result, DispatchTimeGammaResult):
            dispatch_time_gamma: DispatchTimeGamma = dispatch_time_result.dt_gamma
            return DTGammaDTO(
                shape=dispatch_time_gamma.shape,
                scale=dispatch_time_gamma.scale,
                loc=dispatch_time_gamma.loc
                )
        elif isinstance(dispatch_time_result, DispatchTimeSampleResult):
            dispatch_time_sample: DispatchTimeSample = dispatch_time_result.dt_sample
            return DTSampleDTO(x=dispatch_time_result.dt_x, mean=dispatch_time_sample.mean)
        else:
            raise ValueError(f"Unsupported DispatchTimeResult type: {type(dispatch_time_result)}. This should never happen.")
        

    def create_dt_input_dto(
        self,
        site_id: int,
        maybe_shipment_time: Optional[datetime] = None, 
        maybe_dispatch_time_result: Optional[DispatchTimeResult] = None
    ) -> DTInputDTO:
        if maybe_shipment_time is not None:
            return DTShipmentTimeInputDTO(site_id=site_id, shipment_time=maybe_shipment_time)
        
        if maybe_dispatch_time_result is None:
            raise ValueError("Either shipment_time or dispatch_time_result must be provided in DTInputDTO creation.")

        dt_distribution: DTDistributionDTO = self._create_dt_distribution(maybe_dispatch_time_result)
        return DTDistributionInputDTO(site_id=site_id, distribution=dt_distribution)
        

    def create_alpha_base_input_dto(self, shipment_time_result: ShipmentTimeResult, vertex_id: int) -> AlphaBaseInputDTO:
        if isinstance(shipment_time_result, ShipmentTimeGammaResult):
            alpha_dist = AlphaGammaDTO(
                shape=shipment_time_result.dt_gamma.shape,
                scale=shipment_time_result.dt_gamma.scale,
                loc=shipment_time_result.dt_gamma.loc,
            )
        elif isinstance(shipment_time_result, ShipmentTimeSampleResult):
            alpha_dist = AlphaSampleDTO(mean=shipment_time_result.dt_sample.mean)
        else:
            raise ValueError(f"Unsupported ShipmentTimeResult type: {type(shipment_time_result)}. This should never happen.")

        return AlphaBaseInputDTO(st_distribution=alpha_dist, vertex_id=vertex_id)
    
    def create_alpha_input_dto(self, alpha_base_input: AlphaBaseInputDTO) -> AlphaInputDTO:
        return AlphaInputDTO(st_distribution=alpha_base_input.st_distribution, vertex_id=alpha_base_input.vertex_id)


    def create_pt_base_input_dto(self, vertex_id: int, carrier_names: List[str]) -> PTBaseInputDTO:
        return PTBaseInputDTO(vertex_id=vertex_id, carrier_names=carrier_names)

    def create_pt_input_dto(self, pt_base_input: PTBaseInputDTO) -> PTInputDTO:
        return PTInputDTO(
            vertex_id= pt_base_input.vertex_id,
            carrier_names=pt_base_input.carrier_names)


    def create_tt_base_input_dto(self, shipment_time_result: ShipmentTimeResult) -> TTBaseInputDTO:
        if isinstance(shipment_time_result, ShipmentTimeGammaResult):
            tt_dist = TTGammaDTO(
                shape=shipment_time_result.dt_gamma.shape,
                scale=shipment_time_result.dt_gamma.scale,
                loc=shipment_time_result.dt_gamma.loc,
            )
        elif isinstance(shipment_time_result, ShipmentTimeSampleResult):
            tt_dist = TTSampleDTO(x=shipment_time_result.dt_x, mean=shipment_time_result.dt_sample.mean)
        else:
            raise ValueError(f"Unsupported ShipmentTimeResult type: {type(shipment_time_result)}. This should never happen.")

        return TTBaseInputDTO(distribution=tt_dist)
    
    def create_tt_input_dto(self, tt_partial_input: TTBaseInputDTO) -> TTInputDTO:
        return TTInputDTO(distribution=tt_partial_input.distribution)
    
    
    def create_time_deviation_partial_input_dto(
        self, 
        dispatch_time_result: DispatchTimeResult,
        shipment_time_result: ShipmentTimeResult
    ) -> TimeDeviationBaseInputDTO:
        dt_distribution: DTDistributionDTO = self._create_dt_distribution(dispatch_time_result)

        if isinstance(shipment_time_result, ShipmentTimeGammaResult):
            st_dist = STGammaDTO(
                shape=shipment_time_result.dt_gamma.shape,
                scale=shipment_time_result.dt_gamma.scale,
                loc=shipment_time_result.dt_gamma.loc,
            )
        elif isinstance(shipment_time_result, ShipmentTimeSampleResult):
            st_dist = STSampleDTO(x=shipment_time_result.dt_x, mean=shipment_time_result.dt_sample.mean)
    
        return TimeDeviationBaseInputDTO(
            dt_distribution=dt_distribution,
            st_distribution=st_dist
        )

    def create_time_deviation_input_dto(
        self,
        td_partial_input: TimeDeviationBaseInputDTO,
        dt: DT_DTO,
        tfst: TFST_DTO
    ) -> TimeDeviationInputDTO:
        return TimeDeviationInputDTO(td_partial_input=td_partial_input, dt=dt, tfst=tfst)


    