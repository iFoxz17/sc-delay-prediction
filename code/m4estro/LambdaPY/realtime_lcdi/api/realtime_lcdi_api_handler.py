from typing import Dict
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

from api.route.realtime_lcdi_route import register_routes as register_realtime_lcdi_routes
from api.route.sc_graph_route import register_routes as register_sc_graph_routes

from logger import get_logger
logger = get_logger(__name__)

app: APIGatewayRestResolver = APIGatewayRestResolver()

register_realtime_lcdi_routes(app)
register_sc_graph_routes(app)

def handler(event: Dict, context: LambdaContext) -> Dict:
    return app.resolve(event, context)