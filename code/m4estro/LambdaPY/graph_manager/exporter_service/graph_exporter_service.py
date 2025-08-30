from typing import Dict, Any
import igraph as ig
import os

from serializer.s3_graph_serializer import S3GraphSerializer

from exporter_service.graph_exporter import GraphExporter

from logger import get_logger
logger = get_logger(__name__)

def get_graph_data() -> Dict[str, Any]:
    try:
        serializer: S3GraphSerializer = S3GraphSerializer()
        g: ig.Graph = serializer.deserialize()
    except Exception:
        logger.exception("Error during graph serialization")
        raise
    
    logger.debug("Graph deserialized successfully")

    exporter: GraphExporter = GraphExporter()
    try:
        graph_data: Dict[str, Any] = exporter.export_as_graph(g)
    except Exception:
        logger.exception("Error during graph export")
        raise
    
    logger.debug("Graph data exported successfully")
    return graph_data

def get_map_data() -> Dict[str, Any]:
    try:
        serializer: S3GraphSerializer = S3GraphSerializer()
        g: ig.Graph = serializer.deserialize()
    except Exception:
        logger.exception("Error during graph serialization")
        raise
    
    logger.debug("Graph deserialized successfully")

    exporter: GraphExporter = GraphExporter()
    try:
        maps_data: Dict[str, Any] = exporter.export_as_map(g)
    except Exception:
        logger.exception("Error during graph export")
        raise
    
    logger.debug("Map data exported successfully")
    return maps_data