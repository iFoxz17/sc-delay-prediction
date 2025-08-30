'''
import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Union

import igraph as ig

# The function under test
from core.service.calculator_service import compute_order_realtime_lcdi

# Query-result types
from core.query_handler.query_result import (
    ParamsResult,
    DispatchTimeGammaResult,
    DeliveryTimeGammaResult,
)
from model.order import Order
from model.carrier import Carrier
from model.alpha_opt import AlphaOpt
from model.dispatch_time_gamma import DispatchTimeGamma
from model.delivery_time_gamma import DeliveryTimeGamma

# DTO types (we only need to import for annotations; fakes are returned)
from core.calculator.dt.dt_input_dto import (
    DTShipmentTimeInputDTO,
    DTDistributionInputDTO,
)
from core.calculator.tfst.alpha.alpha_input_dto import AlphaPartialInputDTO
from core.calculator.tfst.pt.pt_input_dto import PTPartialInputDTO
from core.calculator.tfst.tt.tt_input_dto import TTPartialInputDTO

# We'll patch these in the service module’s namespace
from core.executor.tfst_executor import TFSTExecutor
from core.executor.executor import Executor
from core.initializer.tfst_initializer import TFSTInitializer
from core.initializer.initializer import Initializer
from core.query_handler.query_handler import QueryHandler
from core.serializer.bucket_data_loader import BucketDataLoader
from service.db_utils import get_db_connector, get_read_only_db_connector


@pytest.fixture(autouse=True)
def patch_environment(monkeypatch):
    # --- BucketDataLoader ----------------------------------------------------------------
    class FakeSCGraph:
        def extract_paths(self, source, carriers):
            return {"paths": []}

    class FakeRouteTimeEstimator:
        def predict(self, dto):
            return [1.0]

    class FakeBucketLoader:
        def __init__(self):
            pass

        def get_bucket_name(self, env_key="TEST_SC_GRAPH_BUCKET_NAME"):
            return "fake-bucket"
        def load_sc_graph(self):
            return FakeSCGraph()
        def load_route_time_estimator(self):
            return FakeRouteTimeEstimator()
        def save_sc_graph(self, sc_graph):
            pass
        def save_dp_managers(self, sc_graph, force=False):
            pass

    monkeypatch.setattr(
        "core.service.calculator_service.BucketDataLoader",
        lambda: FakeBucketLoader()
    )

    # --- DTOFactory ----------------------------------------------------------------------
    class FakeDTOFactory:
        def create_dt_input_dto(self, order_time, shipment_time=None, dispatch_time_result=None):
            # return whatever object; service only passes it along
            return DTShipmentTimeInputDTO(order_time=order_time, shipment_time=shipment_time) \
                if shipment_time else DTDistributionInputDTO(order_time=order_time, distribution=None)      # type: ignore
        def create_alpha_partial_input_dto(self, delivery_time_result, estimation_time):
            return AlphaPartialInputDTO(st_distribution=None, estimation_time=estimation_time)              # type: ignore
        def create_alpha_input_dto(self, alpha_partial_input, shipment_time):
            return object()
        def create_pt_partial_input_dto(self, vertex_id, carrier_names, maybe_event_time, maybe_estimation_time):
            return PTPartialInputDTO(vertex_id=vertex_id, carrier_names=carrier_names, maybe_event_time=maybe_event_time, maybe_estimation_time=maybe_estimation_time)
        def create_pt_input_dto(self, pt_partial_input, shipment_time):
            return object()
        def create_tt_partial_input_dto(self, delivery_time_result, estimation_time):
            return TTPartialInputDTO(distribution=None, estimation_time=estimation_time)        # type: ignore
        def create_tt_input_dto(self, tt_partial_input, shipment_time):
            return object()
        def create_time_deviation_input_dto(self, td_partial_input, dt, tfst):
            return object()
        def create_time_deviation_partial_input_dto(self, dispatch_time_result, delivery_time_result):
            return object()

    monkeypatch.setattr(
        "core.service.calculator_service.DTOFactory",
        FakeDTOFactory
    )

    # --- DB connectors -------------------------------------------------------------------
    class DummySession:
        pass

    class DummyRO:
        def session_scope(self):
            class Ctx:
                def __enter__(self): return DummySession()
                def __exit__(self, *args): pass
            return Ctx()

    class DummyRW(DummyRO):
        pass

    monkeypatch.setattr(
        "core.service.calculator_service.get_read_only_db_connector",
        lambda : DummyRO()
    )
    monkeypatch.setattr(
        "core.service.calculator_service.get_db_connector",
        lambda : DummyRW()
    )

    # --- Initializers & Executors --------------------------------------------------------
    # TFSTInitializer.initialize() must return an object with:
    #   alpha_calculator, pt_calculator, tt_calculator, tfst_calculator
    class DummyTFSTInitResult:
        def __init__(self):
            self.alpha_calculator = object()
            self.pt_calculator = object()
            self.tt_calculator = object()
            self.tfst_calculator = object()

    class DummyTFSTInit:
        def __init__(self, sc_graph, rt_estimator): pass
        def initialize(self, **kwargs):
            return DummyTFSTInitResult()

    # Initializer.initialize() must return an object with:
    #   dt_calculator, tfst_initializer_result, est_calculator, cfdi_calculator, eodt_calculator, edd_calculator
    class DummyInitResult:
        def __init__(self):
            self.dt_calculator = object()
            self.tfst_initializer_result = DummyTFSTInitResult()
            self.est_calculator = object()
            self.cfdi_calculator = object()
            self.eodt_calculator = object()
            self.edd_calculator = object()
            self.time_deviation_calculator = object()

    class DummyInit:
        def __init__(self, tfst_initializer): pass
        def initialize(self, **kwargs):
            return DummyInitResult()

    # Executor.execute() returns an object passed to save_estimated_time
    class DummyExecResult:
        pass

    class DummyTFSTExec:
        def __init__(self, alpha_calculator, pt_calculator, tt_calculator, tfst_calculator, parallelization): pass
        def execute(self, alpha_input, pt_input, tt_input):
            return DummyExecResult()

    class DummyExec:
        def __init__(self, dto_factory, dt_calculator, tfst_calculator_executor,
                     est_calculator, cfdi_calculator, eodt_calculator, edd_calculator, td_calculator): pass
        def execute(self, dt_input, alpha_partial_input, pt_partial_input, tt_partial_input, td_partial_input):
            return DummyExecResult()

    monkeypatch.setattr(
        "core.service.calculator_service.TFSTInitializer",
        DummyTFSTInit
    )
    monkeypatch.setattr(
        "core.service.calculator_service.Initializer",
        DummyInit
    )
    monkeypatch.setattr(
        "core.service.calculator_service.TFSTExecutor",
        DummyTFSTExec
    )
    monkeypatch.setattr(
        "core.service.calculator_service.Executor",
        DummyExec
    )

    # --- QueryHandler --------------------------------------------------------------------
    params = ParamsResult(
        rt_estimator_model_mape=0.1,
        pt_confidence=0.9,
        tt_confidence=0.8,
        dt_time_deviation_confidence=0.95,
        st_time_deviation_confidence=0.9,
        parallelization=0
    )
    dispatch = DispatchTimeGammaResult(dt_gamma=DispatchTimeGamma(shape=1.0, scale=1.0))
    delivery = DeliveryTimeGammaResult(dt_gamma=DeliveryTimeGamma(shape=2.0, scale=2.0))

    carrier = Carrier(id=1, name="C1")
    order = Order(
        id=1,
        site_id=2,
        manufacturer_creation_timestamp=datetime(2024,1,1,8,0, tzinfo=timezone.utc),
        carrier_creation_timestamp=datetime(2024,1,1,10,0, tzinfo=timezone.utc),
        carrier=carrier
    )
    alpha_opt = AlphaOpt(tt_weight=0.5)

    class DummyEstimatedTime:
        id = 0
        vertex_id = 12345
        order_id = 45678

    class DummyQH:
        def __init__(self, session): pass
        def get_params(self): return params
        def get_order(self, order_id): return order
        def get_alpha_opt(self, site_id, carrier_id): return alpha_opt
        def get_dispatch_time(self, site_id): return dispatch
        def get_delivery_time(self, site_id, carrier_id=None): return delivery
        def save_estimated_time(self, **kwargs): return DummyEstimatedTime()

    monkeypatch.setattr(
        "core.service.calculator_service.QueryHandler",
        DummyQH
    )

    class DummyFormatter:
        def format_et(self, et):
            return {
                'vertex': {'id': et.vertex_id},
                'order': {'id': et.order_id},
            }
        
    monkeypatch.setattr(
        "core.service.calculator_service.Formatter",
        DummyFormatter
    )

    yield


def test_with_shipment_time():
    now = datetime(2024,1,1,12,0, tzinfo=timezone.utc)
    vertex = {"v_id": 12345, "name": "Node A", "type": "SUPPLIER_SITE"}
    res = compute_order_realtime_lcdi(
        vertex=vertex,
        order_id=1,
        event_time=now - timedelta(hours=1),
        maybe_estimation_time=now
    )
    assert res['vertex']['id'] == 12345
    assert res['order']['id'] == 45678


def test_without_shipment_time(monkeypatch):
    # Re-patch QueryHandler to remove shipment time on order
    params = ParamsResult(0.1,0.9,0.8,0.95,0.9,0)
    dispatch = DispatchTimeGammaResult(dt_gamma=DispatchTimeGamma(shape=1.0, scale=1.0))
    delivery = DeliveryTimeGammaResult(dt_gamma=DeliveryTimeGamma(shape=2.0, scale=2.0))
    carrier = Carrier(id=1, name="C1")
    order_no_ship = Order(
        id=1, site_id=2,
        manufacturer_creation_timestamp=datetime(2024,1,1,8,0, tzinfo=timezone.utc),
        carrier_creation_timestamp=None,
        carrier=carrier
    )
    alpha_opt = AlphaOpt(tt_weight=0.5)

    class DummyEstimatedTime2:
        id = 0
        vertex_id = 54321
        order_id = 87654

    class DummyQH2:
        def __init__(self, session): pass
        def get_params(self): return params
        def get_order(self, order_id): return order_no_ship
        def get_alpha_opt(self, site_id, carrier_id): return alpha_opt
        def get_dispatch_time(self, site_id): return dispatch
        def get_delivery_time(self, site_id, carrier_id=None): return delivery
        def save_estimated_time(self, **kwargs): return DummyEstimatedTime2()

    monkeypatch.setattr(
        "core.service.calculator_service.QueryHandler",
        DummyQH2
    )

    vertex = {"v_id": 54321, "name": "Node B", "type": "MANUFACTURER"}
    now = datetime(2024,1,2,14,0, tzinfo=timezone.utc)
    res = compute_order_realtime_lcdi(
        vertex=vertex,
        order_id=1,
        event_time=now - timedelta(hours=2),
        maybe_estimation_time=now
    )
    assert res['vertex']['id'] == 54321
    assert res['order']['id'] == 87654
'''