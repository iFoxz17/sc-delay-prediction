import pytest
from unittest.mock import create_autospec, MagicMock
from datetime import datetime, timedelta, timezone

from model.alpha import AlphaType

from core.executor.executor import Executor, ExecutorResult
from core.executor.tfst_executor import TFSTExecutor, TFSTExecutorResult, TFSTCompute

from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO, TimeSequenceInputDTO

from core.calculator.dt.holiday.holiday_dto import HolidayResultDTO
from core.calculator.dt.dt_calculator import DTCalculator
from core.calculator.dt.dt_input_dto import DTInputDTO, DTDistributionInputDTO, DTGammaDTO, DTSampleDTO
from core.calculator.dt.dt_dto import DT_DTO

from core.calculator.tfst.alpha.alpha_input_dto import AlphaBaseInputDTO, AlphaInputDTO, AlphaSampleDTO, AlphaGammaDTO
from core.calculator.tfst.alpha.alpha_dto import AlphaDTO
from core.calculator.tfst.pt.pt_input_dto import PTInputDTO, PTBaseInputDTO
from core.calculator.tfst.pt.pt_dto import PT_DTO
from core.calculator.tfst.tt.tt_dto import TT_DTO
from core.calculator.tfst.tt.tt_input_dto import TTInputDTO, TTBaseInputDTO, TTGammaDTO, TTSampleDTO
from core.calculator.tfst.tfst_dto import TFST_DTO

from core.calculator.est.est_calculator import ESTCalculator
from core.calculator.est.est_dto import EST_DTO
from core.calculator.cfdi.cfdi_calculator import CFDICalculator
from core.calculator.cfdi.cfdi_dto import CFDI_DTO
from core.calculator.eodt.eodt_calculator import EODTCalculator
from core.calculator.eodt.eodt_dto import EODT_DTO
from core.calculator.edd.edd_calculator import EDDCalculator
from core.calculator.edd.edd_dto import EDD_DTO
from core.calculator.time_deviation.time_deviation_calculator import TimeDeviationCalculator
from core.calculator.time_deviation.time_deviation_input_dto import TimeDeviationBaseInputDTO, TimeDeviationInputDTO, STGammaDTO
from core.calculator.time_deviation.time_deviation_dto import TimeDeviationDTO

from core.dto.dto_factory import DTOFactory


@pytest.fixture
def setup_mocks():
    dto_factory = create_autospec(DTOFactory)
    dt_calculator = create_autospec(DTCalculator)
    tfst_executor = create_autospec(TFSTExecutor)
    est_calculator = create_autospec(ESTCalculator)
    cfdi_calculator = create_autospec(CFDICalculator)
    eodt_calculator = create_autospec(EODTCalculator)
    edd_calculator = create_autospec(EDDCalculator)
    td_calculator = create_autospec(TimeDeviationCalculator)

    executor = Executor(
        dto_factory=dto_factory,
        dt_calculator=dt_calculator,
        tfst_calculator_executor=tfst_executor,
        est_calculator=est_calculator,
        cfdi_calculator=cfdi_calculator,
        eodt_calculator=eodt_calculator,
        edd_calculator=edd_calculator,
        td_calculator=td_calculator,
    )

    return {
        "executor": executor,
        "dto_factory": dto_factory,
        "dt_calculator": dt_calculator,
        "tfst_executor": tfst_executor,
        "est_calculator": est_calculator,
        "cfdi_calculator": cfdi_calculator,
        "eodt_calculator": eodt_calculator,
        "edd_calculator": edd_calculator,
        "td_calculator": td_calculator,
    }


def test_executor_execute_returns_expected_results():
    # Define fixed datetimes
    order_time = datetime(2025, 6, 21, 10, tzinfo=timezone.utc)
    shipment_time = order_time + timedelta(hours=1)
    event_time = shipment_time + timedelta(hours=1)
    estimation_time = event_time + timedelta(hours=1)

    # Prepare input DTOs
    dt_input = DTDistributionInputDTO(site_id=1, distribution=DTGammaDTO(shape=2.0, scale=2.5, loc=0.0))
    alpha_partial_input = AlphaBaseInputDTO(
        st_distribution=AlphaSampleDTO(mean=1.0),
    )
    pt_partial_input = PTBaseInputDTO(
        vertex_id=1,
        carrier_names=["carrier1"],
    )
    tt_partial_input = TTBaseInputDTO(
        distribution=TTGammaDTO(shape=2.0, scale=1.0, loc=0.0),
    )
    td_partial_input = TimeDeviationBaseInputDTO(
        dt_distribution=DTGammaDTO(shape=2.0, scale=2.5, loc=0.0),
        st_distribution=STGammaDTO(shape=1.0, scale=1.0, loc=0.0),
    )

    # Mocks
    dto_factory = MagicMock()
    dto_factory.create_alpha_input_dto.return_value = AlphaInputDTO(
        st_distribution=AlphaSampleDTO(mean=1.0),
    )
    dto_factory.create_pt_input_dto.return_value = PTInputDTO(
        vertex_id=1,
        carrier_names=["carrier1"],
    )
    dto_factory.create_tt_input_dto.return_value = TTInputDTO(
        distribution=TTGammaDTO(shape=2.0, scale=1.0, loc=0.0),
    )

    dt_dto: DT_DTO = DT_DTO(
        confidence=0.95,
        elapsed_time=5.0,
        elapsed_working_time=5.0,
        elapsed_holidays=MagicMock(spec=HolidayResultDTO),
        remaining_time_lower=0.0,
        remaining_time=2.0,
        remaining_time_upper=2.0,
        remaining_working_time_lower=0.0,
        remaining_working_time=1.5,
        remaining_working_time_upper=1.5,
        remaining_holidays=MagicMock(spec=HolidayResultDTO),
    )

    dto_factory.create_time_deviation_input_dto.return_value = TimeDeviationInputDTO(
        td_partial_input=td_partial_input,
        dt=dt_dto,
        tfst=TFST_DTO(lower=0.5, upper=1.5, alpha=0.4, tolerance=0.1, computed=TFSTCompute.ALL),
    )
            
    dt_calculator = MagicMock()
    dt_calculator.calculate.return_value = dt_dto
    
    alpha_dto: AlphaDTO = AlphaDTO(input=0.6, value=0.4, type_=AlphaType.CONST)
    pt_dto: PT_DTO = PT_DTO(lower=1.0, upper=3.0, n_paths=2, avg_wmi=0.5, avg_tmi=0.6, tmi_data=[], wmi_data=[], params=MagicMock(from_autospec=True))
    tt_dto: TT_DTO = TT_DTO(lower=1.0, upper=3.0, confidence=0.9)
    tfst_dto: TFST_DTO = TFST_DTO(lower=0.5, upper=1.5, alpha=0.4, tolerance=0.1, computed=TFSTCompute.ALL)
    tfst_result = TFSTExecutorResult(alpha=alpha_dto, pt=pt_dto, tt=tt_dto, tfst=tfst_dto)

    tfst_executor = MagicMock()
    tfst_executor.execute.return_value = tfst_result

    est_calculator = MagicMock()
    est_calculator.calculate.return_value = EST_DTO(value=2.0)

    cfdi_calculator = MagicMock()
    cfdi_calculator.calculate.return_value = CFDI_DTO(lower=0.5, upper=1.5)

    eodt_calculator = MagicMock()
    eodt_calculator.calculate.return_value = EODT_DTO(value=7.0)

    edd_calculator = MagicMock()
    edd_calculator.calculate.return_value = EDD_DTO(value=order_time + timedelta(hours=7))

    td_calculator = MagicMock()
    td_calculator.calculate.return_value = TimeDeviationDTO(
        dt_td_lower=1.0,
        dt_td_upper=1.0,
        st_td_lower=2.0,
        st_td_upper=3.0,
        dt_confidence=0.95,
        st_confidence=0.9
    )

    # Instantiate the executor
    executor = Executor(
        dto_factory=dto_factory,
        dt_calculator=dt_calculator,
        tfst_calculator_executor=tfst_executor,
        est_calculator=est_calculator,
        cfdi_calculator=cfdi_calculator,
        eodt_calculator=eodt_calculator,
        edd_calculator=edd_calculator,
        td_calculator=td_calculator,
    )
    
    time_sequence_input = TimeSequenceInputDTO(
        order_time=order_time,
        event_time=event_time,
        estimation_time=estimation_time
    )

    # Run execution
    result = executor.execute(
        time_sequence_input=time_sequence_input,
        dt_input=dt_input,
        alpha_base_input=alpha_partial_input,
        pt_base_input=pt_partial_input,
        tt_base_input=tt_partial_input,
        td_partial_input=td_partial_input
    )

    # Assertions
    assert isinstance(result, ExecutorResult)
    assert result.dt == dt_dto
    assert result.tfst_executor_result == tfst_result
    assert result.est.value == 2.0
    assert result.cfdi.lower == 0.5
    assert result.cfdi.upper == 1.5
    assert result.eodt.value == 7.0
    assert result.edd.value == order_time + timedelta(hours=7)
