from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import pytest

from core.dto.dto_factory import DTOFactory
from core.query_handler.query_result import (
    DispatchTimeGammaResult, DispatchTimeSampleResult,
    ShipmentTimeGammaResult, ShipmentTimeSampleResult
)
from model.dispatch_time_gamma import DispatchTimeGamma
from model.dispatch_time_sample import DispatchTimeSample
from model.shipment_time import ShipmentTime    
from model.shipment_time_gamma import ShipmentTimeGamma
from model.shipment_time_sample import ShipmentTimeSample


from core.calculator.tfst.tfst_dto import TFST_DTO
from core.calculator.time_deviation.time_deviation_input_dto import (
    TimeDeviationBaseInputDTO, TimeDeviationInputDTO,
    STGammaDTO
)

from core.calculator.dt.dt_input_dto import (
    DTInputDTO, DTDistributionInputDTO, DTShipmentTimeInputDTO,
    DTDistributionDTO, DTGammaDTO, DTSampleDTO
)
from core.calculator.dt.dt_dto import DT_DTO
from core.calculator.tfst.tfst_dto import TFST_DTO
from core.calculator.time_deviation.time_deviation_input_dto import (
    TimeDeviationBaseInputDTO, TimeDeviationInputDTO, STGammaDTO, STSampleDTO
)


@pytest.fixture
def factory():
    return DTOFactory()


def test_create_dt_input_dto_with_dispatch_gamma(factory):
    gamma = DispatchTimeGamma(shape=1.1, scale=2.2, loc=0.0)
    result = DispatchTimeGammaResult(dt_gamma=gamma)
    
    dto = factory.create_dt_input_dto(site_id=1, maybe_dispatch_time_result=result)

    assert dto.site_id == 1
    assert dto.distribution.shape == 1.1
    assert dto.distribution.scale == 2.2
    assert dto.distribution.loc == 0.0


def test_create_dt_input_dto_with_dispatch_sample(factory):
    sample = DispatchTimeSample(mean=3.3)
    result = DispatchTimeSampleResult(dt_sample=sample, dt_x=[1.0, 2.0, 3.0])

    dto = factory.create_dt_input_dto(site_id=9, maybe_dispatch_time_result=result)

    assert dto.site_id == 9
    assert dto.distribution.mean == 3.3


def test_create_dt_input_dto_with_shipment_time(factory):
    shipment_time = datetime(2024, 1, 2)

    dto = factory.create_dt_input_dto(site_id=0, maybe_shipment_time=shipment_time)

    assert isinstance(dto, DTShipmentTimeInputDTO)
    assert dto.site_id == 0
    assert dto.shipment_time == shipment_time


def test_create_alpha_base_input_dto_with_gamma(factory):
    gamma = ShipmentTimeGamma(shape=1.5, scale=2.5, loc=0.5)
    result = ShipmentTimeGammaResult(dt_gamma=gamma)
    
    dto = factory.create_alpha_base_input_dto(shipment_time_result=result, vertex_id=42)

    assert dto.st_distribution.shape == 1.5
    assert dto.st_distribution.scale == 2.5
    assert dto.st_distribution.loc == 0.5
    assert dto.vertex_id == 42


def test_create_alpha_base_input_dto_with_sample(factory):
    sample = ShipmentTimeSample(
        id=1,
        site_id=101,
        carrier_id=202,
        median=4.0,
        mean=4.4,
        std_dev=1.1,
        n=100
    )
    dt1: ShipmentTime = ShipmentTime(site_id=101, carrier_id=202, hours=10)
    dt2: ShipmentTime = ShipmentTime(site_id=101, carrier_id=202, hours=11)
    dt3: ShipmentTime = ShipmentTime(site_id=101, carrier_id=202, hours=5.4)
    
    result = ShipmentTimeSampleResult(dt_sample=sample, dt_x=[dt1, dt2, dt3])

    dto = factory.create_alpha_base_input_dto(shipment_time_result=result, vertex_id=99)

    assert dto.st_distribution.mean == pytest.approx(4.4)
    assert dto.vertex_id == 99


def test_create_alpha_input_dto(factory):
    sample = ShipmentTimeSample(
        id=2,
        site_id=102,
        carrier_id=203,
        median=5.0,
        mean=5.5,
        std_dev=1.2,
        n=80
    )
    dt1: ShipmentTime = ShipmentTime(site_id=102, carrier_id=203, hours=10)
    dt2: ShipmentTime = ShipmentTime(site_id=102, carrier_id=203, hours=11)
    dt3: ShipmentTime = ShipmentTime(site_id=102, carrier_id=203, hours=5.4)
    
    result = ShipmentTimeSampleResult(dt_sample=sample, dt_x=[dt1, dt2, dt3])

    partial = factory.create_alpha_base_input_dto(result, vertex_id=7)
    dto = factory.create_alpha_input_dto(partial)

    assert dto.st_distribution.mean == pytest.approx(5.5)
    assert dto.vertex_id == 7


def test_create_pt_base_and_input_dto(factory):
    vertex_id = 7
    carrier_names = ["CarrierA"]

    partial = factory.create_pt_base_input_dto(vertex_id, carrier_names)
    dto = factory.create_pt_input_dto(partial)

    assert dto.vertex_id == vertex_id
    assert dto.carrier_names == carrier_names


def test_create_tt_base_input_dto_with_gamma(factory):
    gamma = ShipmentTimeGamma(shape=2.2, scale=1.1, loc=0.1)
    result = ShipmentTimeGammaResult(dt_gamma=gamma)

    dto = factory.create_tt_base_input_dto(result)

    assert dto.distribution.shape == 2.2
    assert dto.distribution.scale == 1.1
    assert dto.distribution.loc == 0.1


def test_create_tt_base_input_dto_with_sample(factory):
    result = ShipmentTimeSampleResult(dt_sample=Mock(), dt_x=[1.0, 2.0, 3.0])

    dto = factory.create_tt_base_input_dto(result)

    assert dto.distribution.x == [1.0, 2.0, 3.0]


def test_create_tt_input_dto(factory):
    result = ShipmentTimeSampleResult(dt_sample=Mock(), dt_x=[4.0, 5.0])

    partial = factory.create_tt_base_input_dto(result)
    dto = factory.create_tt_input_dto(partial)

    assert dto.distribution.x == [4.0, 5.0]


def test_create_time_deviation_partial_input_dto_with_gamma(factory):
    dispatch_gamma = DispatchTimeGamma(shape=2.0, scale=3.0, loc=1.0)
    delivery_gamma = ShipmentTimeGamma(shape=4.0, scale=1.5, loc=0.5)

    dispatch_result = DispatchTimeGammaResult(dt_gamma=dispatch_gamma)
    delivery_result = ShipmentTimeGammaResult(dt_gamma=delivery_gamma)

    partial_dto: TimeDeviationBaseInputDTO = factory.create_time_deviation_partial_input_dto(
        dispatch_time_result=dispatch_result,
        shipment_time_result=delivery_result
    )
    assert isinstance(partial_dto.dt_distribution, DTGammaDTO)
    dt_gamma_partial_dto: DTGammaDTO = partial_dto.dt_distribution

    assert isinstance(partial_dto.st_distribution, STGammaDTO)
    st_gamma_partial_dto: STGammaDTO = partial_dto.st_distribution

    
    assert isinstance(partial_dto, TimeDeviationBaseInputDTO)
    assert dt_gamma_partial_dto.shape == 2.0
    assert st_gamma_partial_dto.shape == 4.0
    assert isinstance(partial_dto.st_distribution, STGammaDTO)


def test_create_time_deviation_base_input_dto_with_sample(factory):
    dispatch_sample = DispatchTimeSample(mean=2.5)
    delivery_sample = ShipmentTimeSample(
        id=3,
        site_id=103,
        carrier_id=204,
        median=6.0,
        mean=6.5,
        std_dev=1.3,
        n=120
    )
    
    dispatch_result = DispatchTimeSampleResult(dt_sample=dispatch_sample, dt_x=[1.0, 2.0, 3.0])
    delivery_result = ShipmentTimeSampleResult(dt_sample=delivery_sample, dt_x=[5.0, 6.0, 7.0])

    partial_dto: TimeDeviationBaseInputDTO = factory.create_time_deviation_partial_input_dto(
        dispatch_time_result=dispatch_result,
        shipment_time_result=delivery_result
    )
    assert isinstance(partial_dto.dt_distribution, DTSampleDTO)
    dt_sample_partial_dto: DTSampleDTO = partial_dto.dt_distribution

    assert isinstance(partial_dto.st_distribution, STSampleDTO)
    st_sample_partial_dto: STSampleDTO = partial_dto.st_distribution

    assert isinstance(partial_dto, TimeDeviationBaseInputDTO)
    assert dt_sample_partial_dto.mean == 2.5
    assert st_sample_partial_dto.mean == 6.5
    assert isinstance(partial_dto.st_distribution, STSampleDTO)
    assert st_sample_partial_dto.x == [5.0, 6.0, 7.0]


def test_create_time_deviation_input_dto(factory):
    partial = Mock(spec=TimeDeviationBaseInputDTO)
    dt = Mock(spec=DT_DTO)
    tfst = Mock(spec=TFST_DTO)

    full_dto = factory.create_time_deviation_input_dto(
        td_partial_input=partial,
        dt=dt,
        tfst=tfst,
    )

    assert isinstance(full_dto, TimeDeviationInputDTO)
    assert full_dto.td_partial_input == partial
    assert full_dto.dt == dt
    assert full_dto.tfst == tfst