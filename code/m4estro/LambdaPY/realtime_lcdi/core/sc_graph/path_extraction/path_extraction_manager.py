from typing import Optional, List, Union, Any
from enum import Enum
import igraph as ig
import numpy as np

from model.vertex import VertexType

from graph_config import V_ID_ATTR, TYPE_ATTR
from core.sc_graph.utils import VertexIdentifier, PathIndex, Path, resolve_path, resolve_vertex

from core.sc_graph.path_extraction.path_dp_manager import PathDPManager, VertexPathDPManager

from logger import get_logger
logger = get_logger(__name__)

class DFSColor(Enum):
    UNVISITED = 0
    VISITING = 1
    VISITED = 2

class PathExtractionManager:
    def __init__(self, graph: ig.Graph, maybe_manufacturer: Optional[ig.Vertex] = None, maybe_dp_manager: Optional[PathDPManager] = None):
        self.graph: ig.Graph = graph
        self.manufacturer: ig.Vertex = maybe_manufacturer or graph.vs.find(**{TYPE_ATTR: VertexType.MANUFACTURER.value}) 
        self.dp_manager: PathDPManager = maybe_dp_manager or PathDPManager(graph.vcount())
    
    def _finalize_paths(self, source: ig.Vertex, paths: List[PathIndex], by: VertexIdentifier) -> List[Path]:
        source_identifier: int | str
        
        match by:
            case VertexIdentifier.INDEX:
                source_identifier = source.index
                logger.debug(f"Finalizing paths by index: {source_identifier}")
            case VertexIdentifier.ID:
                source_identifier = source[V_ID_ATTR]
                logger.debug(f"Finalizing paths by ID: {source_identifier}")
            case VertexIdentifier.NAME:
                source_identifier = source['name']
                logger.debug(f"Finalizing paths by name: {source_identifier}")
            case _:
                logger.error(f"Invalid vertex identifier: {by}. Expected one of {list(VertexIdentifier)}.")
                raise ValueError(f"Invalid vertex identifier: {by}. Expected one of {list(VertexIdentifier)}.")

        finalized_paths: List[List[Any]] = []    
        for path in paths:
            resolved_path: List[Any] = resolve_path(self.graph, path, by)
            resolved_path.insert(0, source_identifier)
            finalized_paths.append(resolved_path)

        return finalized_paths
    
    def extract_paths(self,
                      source: Union[int, str, ig.Vertex], 
                      destination: Optional[Union[int, str, ig.Vertex]] = None,
                      by: VertexIdentifier = VertexIdentifier.INDEX,
                      ) -> List[Path]:
        """
        Extract all possible paths from source to destination (or manufacturer by default)
        """
        def dfs(v: ig.Vertex) -> None:
            v_index: int = v.index
            color[v_index] = DFSColor.VISITING.value

            if not target_v_dp_manager.contains(v_index):
                if v == target_v:
                    target_v_dp_manager.add(v_index, [])
                    color[v_index] = DFSColor.VISITED.value
                    return

                for u_index in self.graph.neighbors(v, mode="out"):
                    if color[u_index] == DFSColor.VISITING.value:
                        logger.error(f"Cycle detected: {v['name']} -> {self.graph.vs[u_index]['name']}. Check data integrity.")
                        continue

                    if color[u_index] == DFSColor.UNVISITED.value:
                        dfs(self.graph.vs[u_index])

                    if target_v_dp_manager.contains(u_index):
                        u_paths: List[PathIndex] = target_v_dp_manager.get(u_index)
                        for u_path in u_paths:
                            v_path: PathIndex = [u_index] + u_path
                            target_v_dp_manager.add(v_index, v_path)

            color[v_index] = DFSColor.VISITED.value
            
        g: ig.Graph = self.graph

        source_v: ig.Vertex = resolve_vertex(g, source)
        target_v: ig.Vertex = resolve_vertex(g, self.manufacturer) if destination is None else resolve_vertex(g, destination)

        source_index, target_index = source_v.index, target_v.index
        source_id, target_id = source_v[V_ID_ATTR], target_v[V_ID_ATTR]
        source_name, target_name = source_v['name'], target_v['name']

        logger.debug(f"Extracting paths from source vertex {source_name} (ID: {source_id}) to destination vertex {target_name} (ID: {target_id})")
        
        target_v_dp_manager: VertexPathDPManager = self.dp_manager.get(target_index)
        color: np.ndarray = np.full(g.vcount(), DFSColor.UNVISITED.value, dtype=int)

        if not target_v_dp_manager.contains(source_v.index):
            logger.debug(f"No DP paths cached for source vertex {source_name} (index {source_index}). Starting DFS.")
            dfs(source_v)
        else:
            logger.debug(f"DP paths already cached for source vertex {source_name} (index {source_index}). Skipping DFS.")

        paths: List[PathIndex] = target_v_dp_manager.get(source_index)
        logger.debug(f"Extracted {len(paths)} paths from source vertex {source_name} to destination vertex {target_name}.")

        return self._finalize_paths(source_v, paths, by)