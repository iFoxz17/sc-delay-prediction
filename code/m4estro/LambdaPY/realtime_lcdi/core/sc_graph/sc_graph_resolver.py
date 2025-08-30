from typing import Optional, override
from dataclasses import dataclass

from graph_config import TYPE_ATTR
from model.vertex import VertexType

from service.lambda_client.geo_service_lambda_client import GeoServiceLambdaClient

from resolver.vertex_resolver import VertexResolver, VertexResult
from resolver.vertex_dto import VertexDTO

from core.serializer.bucket_data_loader import BucketDataLoader
from core.sc_graph.sc_graph import SCGraph

@dataclass
class SCGraphVertexResult(VertexResult):
    sc_graph: SCGraph

class SCGraphResolver(VertexResolver):
    def __init__(self, lambda_client: GeoServiceLambdaClient, maybe_sc_graph: Optional[SCGraph] = None) -> None:
        sc_graph: SCGraph = maybe_sc_graph or BucketDataLoader().load_sc_graph()
        
        super().__init__(graph=sc_graph.graph, lambda_client=lambda_client)
        self.sc_graph: SCGraph = sc_graph

    @override
    def resolve(self, vertex_dto: VertexDTO) -> SCGraphVertexResult:
        vertex_result: VertexResult = super().resolve(vertex_dto)

        return SCGraphVertexResult(vertex=vertex_result.vertex, sc_graph=self.sc_graph)