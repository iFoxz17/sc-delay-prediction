from enum import Enum
from typing import List, Union, Any
import igraph as ig

from graph_config import V_ID_ATTR

class IndexOutOfBoundsException(Exception):
    def __init__(self, index: int, n: int) -> None:
        super().__init__(f"Index {index} is out of bounds for n={n}")
        self.index: int = index
        self.n: int = n

class CarrierNotFoundException(Exception):
    def __init__(self, carrier: str) -> None:
        super().__init__(f"Carrier '{carrier}' not found in the DP manager.")
        self.carrier: str = carrier


def is_legal_index(v_index: int, n: int) -> bool:
    return 0 <= v_index < n


class VertexIdentifier(Enum):
    INDEX = "index"
    ID = V_ID_ATTR
    NAME = "name"

    @classmethod
    def from_str(cls, value: str) -> 'VertexIdentifier':
        try:
            return cls(value)
        except ValueError:
            logger.warning(f"Invalid vertex identifier: {value}. Defaulting to INDEX.")
            return VertexIdentifier.ID


PathIndex = List[int]
PathId = List[int]
PathName = List[str]
Path = Union[PathIndex, PathId, PathName]

from logger import get_logger
logger = get_logger(__name__)

def resolve_vertex(graph: ig.Graph, vertex: Union[int, str, ig.Vertex]) -> ig.Vertex:
    if isinstance(vertex, int):
        resolved: ig.Vertex = graph.vs.find(**{V_ID_ATTR: vertex})
        logger.debug(f"Resolved vertex id {vertex} to vertex {resolved['name']} (index {resolved.index})")
        return resolved
    elif isinstance(vertex, str):
        resolved: ig.Vertex = graph.vs.find(name=vertex)
        logger.debug(f"Resolved vertex name '{vertex}' to vertex {resolved['name']} (index {resolved.index})")
        return resolved
    elif isinstance(vertex, ig.Vertex):
        logger.debug(f"Vertex provided directly: {vertex['name']} (index {vertex.index})")
        return vertex
    else:
        logger.debug(f"Invalid vertex type provided: {type(vertex)}")
        raise ValueError(f"Invalid vertex type: {type(vertex)}. Expected int, str or ig.Vertex.")

def resolve_path(graph: ig.Graph, path: PathIndex, by: VertexIdentifier) -> Path:
        finalized_path: List[Any] = []
        match by:
            case VertexIdentifier.INDEX:
                finalized_path = [path_index for path_index in path]
            case VertexIdentifier.ID:
                finalized_path = [graph.vs[v_index][V_ID_ATTR] for v_index in path]
            case VertexIdentifier.NAME:
                finalized_path = [graph.vs[v_index]['name'] for v_index in path]
            case _:
                raise ValueError(f"Invalid vertex identifier: {by}. Expected one of {list(VertexIdentifier)}.")
            
        
        return finalized_path