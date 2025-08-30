from typing import Optional, List, Dict, Union, Set, cast
from enum import Enum
from collections import defaultdict
import igraph as ig
import numpy as np

from model.vertex import VertexType

from graph_config import TYPE_ATTR

from core.dto.path.prob_path_dto import ProbPathIdDTO
from core.dto.path.paths_dto import PathsIdDTO, PathsNameDTO

from core.sc_graph.path_extraction.path_extraction_manager import PathExtractionManager
from core.sc_graph.path_prob.path_prob_manager import PathProbManager
from core.sc_graph.utils import VertexIdentifier, PathIndex, Path

from logger import get_logger

logger = get_logger(__name__)

class SCGraph:
    def __init__(self, graph: ig.Graph, path_extraction_manager: PathExtractionManager, path_prob_manager: PathProbManager, maybe_manufacturer: Optional[ig.Vertex] = None):
        self.graph: ig.Graph = graph
        self.manufacturer: ig.Vertex = maybe_manufacturer or graph.vs.find(**{TYPE_ATTR: VertexType.MANUFACTURER.value})
        
        self.path_extraction_manager: PathExtractionManager = path_extraction_manager
        self.path_prob_manager: PathProbManager = path_prob_manager

    def extract_paths(self, 
                      source: Union[int, str, ig.Vertex], 
                      carriers: List[str], 
                      zero_prob_paths: bool = False,
                      by: VertexIdentifier = VertexIdentifier.ID) -> PathsIdDTO | PathsNameDTO:
        
        paths: List[Path] = self.path_extraction_manager.extract_paths(
            source=source,
            destination=self.manufacturer,
            by=VertexIdentifier.INDEX
        )

        return self.path_prob_manager.compute_paths_prob(
            source=source,
            carriers=carriers,
            paths=cast(List[PathIndex], paths),
            zero_prob_paths=zero_prob_paths,
            by=by
        )


    
   