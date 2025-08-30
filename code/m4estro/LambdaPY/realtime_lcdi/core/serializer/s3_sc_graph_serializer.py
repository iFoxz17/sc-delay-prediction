from typing import Optional
import igraph as ig

from graph_config import TYPE_ATTR

from serializer.s3_graph_serializer import S3GraphSerializer

from core.sc_graph.sc_graph import SCGraph

from core.sc_graph.path_extraction.path_extraction_manager import PathExtractionManager
from core.sc_graph.path_extraction.path_dp_manager import PathDPManager

from core.sc_graph.path_prob.path_prob_manager import PathProbManager
from core.sc_graph.path_prob.path_prob_dp_manager import PathProbDPManager

from core.serializer.dp.s3_path_dp_manager_serializer import S3PathDPManagerSerializer
from core.serializer.dp.s3_path_prob_dp_manager_serializer import S3PathProbDPManagerSerializer

from model.vertex import VertexType

from logger import get_logger
logger = get_logger(__name__)

class S3SCGraphSerializer:
    def __init__(self, 
                 graph_serializer: Optional[S3GraphSerializer] = None,
                 path_dp_manager_serializer: Optional[S3PathDPManagerSerializer] = None,
                 path_prob_dp_manager_serializer: Optional[S3PathProbDPManagerSerializer] = None,
                 ):
        
        self.graph_serializer: S3GraphSerializer = graph_serializer or S3GraphSerializer()
        self.path_dp_manager_serializer: S3PathDPManagerSerializer = path_dp_manager_serializer or S3PathDPManagerSerializer()
        self.path_prob_dp_manager_serializer: S3PathProbDPManagerSerializer = path_prob_dp_manager_serializer or S3PathProbDPManagerSerializer()

    def serialize_graph(self, graph: ig.Graph, bucket_name: str) -> None:
        self.graph_serializer.serialize(graph, bucket_name)

    def serialize_dp_managers(self, path_extraction_manager: PathExtractionManager, path_prob_manager: PathProbManager, bucket_name: str, force: bool = False) -> None:
        self.path_dp_manager_serializer.serialize(path_extraction_manager.dp_manager, bucket_name, force=force)
        self.path_prob_dp_manager_serializer.serialize(path_prob_manager.dp_manager, bucket_name, force=force)

    def serialize(self, sc_graph: SCGraph, bucket_name: str, force: bool = False) -> None:
        self.serialize_graph(sc_graph.graph, bucket_name)
        self.serialize_dp_managers(
            path_extraction_manager=sc_graph.path_extraction_manager,
            path_prob_manager=sc_graph.path_prob_manager,
            bucket_name=bucket_name,
            force=force
        )

    def deserialize(self, bucket_name: str) -> SCGraph:
        graph: ig.Graph = self.graph_serializer.deserialize(bucket_name)
        try:
            manufacturer: ig.Vertex = graph.vs.find(**{TYPE_ATTR: VertexType.MANUFACTURER.value})
        except ValueError:
            logger.error("Could not initialize SCGraph: Manufacturer vertex not found")
            raise ValueError("Could not initialize SCGraph: Manufacturer vertex not found")

        maybe_path_dp_manager: Optional[PathDPManager] = self.path_dp_manager_serializer.deserialize(bucket_name)
        path_extraction_manager: PathExtractionManager = PathExtractionManager(
            graph=graph,
            maybe_manufacturer=manufacturer,
            maybe_dp_manager=maybe_path_dp_manager
        )
        logger.debug("PathExtractionManager initialized successfully")

        maybe_path_prob_dp_manager: Optional[PathProbDPManager] = self.path_prob_dp_manager_serializer.deserialize(bucket_name)
        path_prob_manager: PathProbManager = PathProbManager(
            graph=graph,
            maybe_manufacturer=manufacturer,
            maybe_dp_manager=maybe_path_prob_dp_manager
        )
        logger.debug("PathProbManager initialized successfully")

        sc_graph: SCGraph = SCGraph(graph=graph, 
                                    maybe_manufacturer=manufacturer, 
                                    path_extraction_manager=path_extraction_manager,
                                    path_prob_manager=path_prob_manager
                                    )
        logger.debug("SCGraph initialized successfully")
        
        return sc_graph