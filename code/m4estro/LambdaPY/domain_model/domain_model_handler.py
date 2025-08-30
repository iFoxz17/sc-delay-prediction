from typing import Dict
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

from model_route.order_route import register_routes as register_order_routes
from model_route.vertex_route import register_routes as register_vertex_routes

from logger import get_logger
logger = get_logger(__name__)

app: APIGatewayRestResolver = APIGatewayRestResolver()

register_order_routes(app)
register_vertex_routes(app)

def handler(event: Dict, context: LambdaContext) -> Dict:
    return app.resolve(event, context)