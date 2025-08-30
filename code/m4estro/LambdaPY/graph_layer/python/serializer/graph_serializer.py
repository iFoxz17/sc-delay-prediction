from typing import List, Tuple, Any, Optional
from abc import ABC, abstractmethod
import igraph as ig

VERTEX_NAME_ATTR = 'name'

class GraphSerializer(ABC):
    def __init__(self, vertex_name_attr: str = VERTEX_NAME_ATTR):
        assert isinstance(vertex_name_attr, str)

        self.vertex_name_attr = vertex_name_attr

    def to_json(self, graph: ig.Graph) -> Tuple[List[Any], List[Any]]:
        if graph.vcount() == 0:
            return ([], [])
        
        return graph.to_dict_list(use_vids=False, vertex_name_attr=self.vertex_name_attr)

    def from_json(self, g_data: Tuple[List[Any], List[Any]]) -> ig.Graph:
        if not g_data:
            return ig.Graph(directed=True)
        
        return ig.Graph.DictList(g_data[0], g_data[1], directed=True, vertex_name_attr=self.vertex_name_attr)

    @abstractmethod
    def serialize(self, graph: ig.Graph, path: Optional[str] = None, filename: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def deserialize(self, path: Optional[str] = None, filename: Optional[str] = None) -> ig.Graph:
        pass