from typing import Tuple, List, Any, override, Optional
import json
import boto3
import igraph as ig

from serializer.graph_serializer import GraphSerializer

s3 = boto3.client('s3')

from utils.config import SC_GRAPH_BUCKET_NAME_KEY, get_env
GRAPH_KEY = 'sc_graph.json'

from logger import get_logger
logger = get_logger(__name__)

class S3GraphSerializer(GraphSerializer):
    def __init__(self):
        super().__init__()
        self.bucket_name: str = get_env(SC_GRAPH_BUCKET_NAME_KEY)
        
    def _get_bucket_paths(self, maybe_bucket_name: Optional[str], maybe_key: Optional[str]) -> Tuple[str, str]:
        key: str = maybe_key or GRAPH_KEY
        bucket_name: str = maybe_bucket_name or self.bucket_name
        return bucket_name, key

    @override
    def serialize(self, graph: ig.Graph, path: Optional[str] = None, filename: Optional[str] = None) -> None:
        bucket_name, key = self._get_bucket_paths(path, filename)
        try:
            g_data: Tuple[List[Any], List[Any]] = self.to_json(graph)
        except Exception:
            logger.exception(f"Error converting graph to serializable format")
            raise
        
        logger.debug(f"Graph converted to serializable format successfully")
        
        try:
            s3.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=json.dumps(g_data).encode('utf-8'),
                ContentType='application/json'
            )
        except Exception:
            logger.exception(f"Error serializing graph data to {bucket_name}/{key}")
            raise
        
        logger.debug(f"Graph serialized successfully to {bucket_name}/{key}")

    @override
    def deserialize(self, path: Optional[str] = None, filename: Optional[str] = None) -> ig.Graph:
        bucket_name, key = self._get_bucket_paths(path, filename) 
        try:
            response = s3.get_object(Bucket=bucket_name, Key=key)
            content: str = response['Body'].read().decode('utf-8')
            g_data: Any = json.loads(content)
        except Exception:
            logger.exception(f"Error retrieving graph data from {bucket_name}/{key}")
            raise
        
        logger.debug(f"Graph data retrieved successfully from {bucket_name}/{key}")
        
        try:
            graph: ig.Graph = self.from_json(g_data)
        except Exception:
            logger.exception(f"Error initializing graph from data")
            raise
        
        logger.debug("Graph initialized successfully")
        return graph