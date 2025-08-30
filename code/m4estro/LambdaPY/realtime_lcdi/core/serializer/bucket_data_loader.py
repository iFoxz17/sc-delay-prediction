from typing import Optional

from utils.config import SC_GRAPH_BUCKET_NAME_KEY, get_env

from core.sc_graph.sc_graph import SCGraph

from core.serializer.s3_sc_graph_serializer import S3SCGraphSerializer

from logger import get_logger
logger = get_logger(__name__)

class BucketDataLoader:
    def __init__(self, maybe_sc_graph_serializer: Optional[S3SCGraphSerializer] = None) -> None:
        self.sc_graph_serializer: S3SCGraphSerializer = maybe_sc_graph_serializer or S3SCGraphSerializer()
        self.bucket_name: str = get_env(SC_GRAPH_BUCKET_NAME_KEY)

    def load_sc_graph(self) -> SCGraph:
        sc_graph: SCGraph = self.sc_graph_serializer.deserialize(bucket_name=self.bucket_name)
        return sc_graph
    
    def save_sc_graph(self, sc_graph: SCGraph, force: bool = False) -> None:
        self.sc_graph_serializer.serialize(sc_graph=sc_graph, bucket_name=self.bucket_name, force=force)
    
    def save_dp_managers(self, sc_graph: SCGraph, force: bool = False) -> None:
        self.sc_graph_serializer.serialize_dp_managers(
            path_extraction_manager=sc_graph.path_extraction_manager,
            path_prob_manager=sc_graph.path_prob_manager,
            bucket_name=self.bucket_name,
            force=force)
