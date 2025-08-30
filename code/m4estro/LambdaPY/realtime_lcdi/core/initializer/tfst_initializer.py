from dataclasses import dataclass

from utils.config import EXTERNAL_API_LAMBDA_ARN_KEY, RT_ESTIMATOR_LAMBDA_ARN_KEY, get_env

from service.lambda_client.traffic_service_lambda_client import TrafficServiceLambdaClient
from service.lambda_client.weather_service_lambda_client import WeatherServiceLambdaClient
from core.calculator.tfst.pt.route_time.rt_estimator_lambda_client import RTEstimatorLambdaClient

from core.sc_graph.sc_graph import SCGraph
from core.query_handler.params.params_result import TFSTParams, PTParams, TTParams

from core.calculator.tfst.pt.tmi.calculator.tmi_calculator import TMICalculator
from core.calculator.tfst.pt.tmi.tmi_manager import TMIManager

from core.calculator.tfst.pt.wmi.calculator.wmi_calculator import WMICalculator
from core.calculator.tfst.pt.wmi.wmi_manager import WMIManager

from core.calculator.tfst.pt.route_time.route_time_estimator import RouteTimeEstimator 
from core.calculator.tfst.pt.route_time.route_time_calculator import RouteTimeCalculator

from core.calculator.tfst.pt.vertex_time.vertex_time_calculator import VertexTimeCalculator

from core.calculator.tfst.pt.pt_calculator import PTCalculator
from core.calculator.tfst.tt.tt_calculator import TTCalculator
from core.calculator.tfst.alpha.alpha_calculator import AlphaCalculator

from core.calculator.tfst.tfst_calculator import TFSTCalculator

from core.initializer.alpha_initializer import AlphaInitializer

from logger import get_logger
logger = get_logger(__name__)

@dataclass
class TFSTInitializerResult:
    alpha_calculator: AlphaCalculator
    pt_calculator: PTCalculator
    tt_calculator: TTCalculator
    tfst_calculator: TFSTCalculator

class TFSTInitializer:
    def __init__(self, alpha_initializer: AlphaInitializer, sc_graph: SCGraph) -> None:
        self.alpha_initializer: AlphaInitializer = alpha_initializer
        self.sc_graph: SCGraph = sc_graph
        
    def initialize(self, tfst_params: TFSTParams) -> TFSTInitializerResult:
        alpha_params = tfst_params.alpha_params
        pt_params: PTParams = tfst_params.pt_params
        tt_params: TTParams = tfst_params.tt_params
        
        rt_estimator_client: RTEstimatorLambdaClient = RTEstimatorLambdaClient(lambda_arn=get_env(RT_ESTIMATOR_LAMBDA_ARN_KEY))
        rt_estimator: RouteTimeEstimator = RouteTimeEstimator(rt_estimator_client=rt_estimator_client, use_model=pt_params.rte_estimator_params.use_model)
        logger.debug(f"RT Estimator initialized successfully")

        rt_calculator: RouteTimeCalculator = RouteTimeCalculator(estimator=rt_estimator, mape=pt_params.rte_estimator_params.model_mape)
        logger.debug("Route time calculator initialized successfully")

        vt_calculator: VertexTimeCalculator = VertexTimeCalculator()
        logger.debug("Vertex time calculator initialized successfully")
        
        tmi_calculator: TMICalculator = TMICalculator(
            tmi_speed_params=pt_params.tmi_params.speed_parameters,
            tmi_distance_params=pt_params.tmi_params.distance_parameters
        )
        logger.debug("TMI calculator initialized successfully")

        wmi_calculator: WMICalculator = WMICalculator()
        logger.debug("WMI calculator initialized successfully")

        external_api_lambda_arn: str = get_env(EXTERNAL_API_LAMBDA_ARN_KEY)
        logger.debug(f"External API lambda ARN: {external_api_lambda_arn}")

        traffic_service_client: 'TrafficServiceLambdaClient' = TrafficServiceLambdaClient(lambda_arn=external_api_lambda_arn,)
        logger.debug("Traffic service lambda client initialized successfully")

        weather_service_client: 'WeatherServiceLambdaClient' = WeatherServiceLambdaClient(lambda_arn=external_api_lambda_arn)
        logger.debug("Weather service lambda client initialized successfully")

        tmi_manager: TMIManager = TMIManager(
            lambda_client=traffic_service_client,
            calculator=tmi_calculator,
            use_traffic_service=pt_params.tmi_params.use_traffic_service,
            max_timedelta=pt_params.tmi_params.traffic_max_timedelta
        )
        logger.debug("TMI manager initialized successfully")

        wmi_manager: WMIManager = WMIManager(
            lambda_client=weather_service_client,
            calculator=wmi_calculator,
            params=pt_params.wmi_params,
        )
        logger.debug("WMI manager initialized successfully")
        
        alpha_calculator: AlphaCalculator = self.alpha_initializer.initialize(alpha_type=alpha_params.alpha_type)
        logger.debug("Alpha calculator initialized successfully")
        
        pt_calculator = PTCalculator(
            sc_graph=self.sc_graph,
            vt_calculator=vt_calculator,
            rt_calculator=rt_calculator,
            tmi_manager=tmi_manager,
            wmi_manager=wmi_manager,
            params=pt_params
        )
        logger.debug("PT calculator initialized successfully")

        tt_calculator: TTCalculator = TTCalculator(confidence=tt_params.confidence)
        logger.debug("TT calculator initialized successfully")

        tfst_calculator: TFSTCalculator = TFSTCalculator()
        logger.debug("TFST calculator initialized successfully")

        return TFSTInitializerResult(
            alpha_calculator=alpha_calculator,
            pt_calculator=pt_calculator,
            tt_calculator=tt_calculator,
            tfst_calculator=tfst_calculator
        )