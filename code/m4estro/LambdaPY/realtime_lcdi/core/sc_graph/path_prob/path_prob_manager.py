from typing import Optional, List, Dict, Union, Set, Any, cast
import igraph as ig
from collections import defaultdict

from graph_config import N_ORDERS_BY_CARRIER_ATTR, V_ID_ATTR, TYPE_ATTR

from model.vertex import VertexType

from core.sc_graph.utils import VertexIdentifier, PathIndex, PathId, PathName, Path, VertexIdentifier, resolve_path, resolve_vertex
from core.sc_graph.path_prob.path_prob_dp_manager import PathProbDPManager

from core.dto.path.paths_dto import PathsIdDTO, PathsNameDTO
from core.dto.path.prob_path_dto import ProbPathIdDTO, ProbPathNameDTO

from logger import get_logger
logger = get_logger(__name__)

class PathProbManager:
    def __init__(self, graph: ig.Graph, maybe_manufacturer: Optional[ig.Vertex] = None, maybe_dp_manager: Optional[PathProbDPManager] = None) -> None:
        self.graph: ig.Graph = graph
        self.manufacturer: ig.Vertex = maybe_manufacturer or graph.vs.find(**{TYPE_ATTR: VertexType.MANUFACTURER.value})
        self.dp_manager: PathProbDPManager = maybe_dp_manager or PathProbDPManager(graph.vcount())

    def _validate_carriers(self, requested_carriers: List[str], legal_carriers: Set[str]) -> Set[str]:
        logger.debug(f"Carriers requested: {requested_carriers}")
        valid_carriers: Set[str] = set(requested_carriers) & legal_carriers
        logger.debug(f"Carriers validated: {valid_carriers}")

        return valid_carriers

    def _compute_path_probability(
        self,
        carrier: str,
        path: PathIndex
    ) -> float:
        g: ig.Graph = self.graph
        prob: float = 1
        i: int = 0
        
        while prob > 0 and i < len(path) - 1:
            v_index: int = path[i]
            u_index: int = path[i + 1]
            v: ig.Vertex = g.vs[v_index]
            u: ig.Vertex = g.vs[u_index]

            edge_id: int = g.get_eid(v_index, u_index, error=False)
            edge: ig.Edge = g.es[edge_id]

            if carrier not in v[N_ORDERS_BY_CARRIER_ATTR]:
                logger.debug(f"Carrier '{carrier}' not found in vertex '{v['name']}': setting probability to 0.")
                return 0.0

            if carrier not in edge[N_ORDERS_BY_CARRIER_ATTR]:
                logger.debug(f"Carrier '{carrier}' not found in edge from '{v['name']}' to '{u['name']}': setting probability to 0.")
                return 0.0

            v_n_orders: int = v[N_ORDERS_BY_CARRIER_ATTR].get(carrier, 0)
            e_n_orders: int = edge[N_ORDERS_BY_CARRIER_ATTR].get(carrier, 0)

            prob: float = (prob * e_n_orders / v_n_orders) if v_n_orders > 0 else 0.0
            i += 1

        return prob
    
    def _get_empty_paths_dto(self, source: ig.Vertex, target: ig.Vertex, requested_carriers: List[str], by: VertexIdentifier) -> PathsIdDTO | PathsNameDTO:
        match by:
            case VertexIdentifier.INDEX:
                logger.debug(f"Returning empty PathsIdDTO for source index {source.index} and target index {target.index}.")
                return PathsIdDTO(source=source.index, destination=target.index, requestedCarriers=requested_carriers, validCarriers=[], paths=[])
            case VertexIdentifier.ID:
                logger.debug(f"Returning empty PathsIdDTO for source ID {source[V_ID_ATTR]} and target ID {target[V_ID_ATTR]}.")
                return PathsIdDTO(source=source[V_ID_ATTR], destination=target[V_ID_ATTR], requestedCarriers=requested_carriers, validCarriers=[], paths=[])
            case VertexIdentifier.NAME:
                logger.debug(f"Returning empty PathsNameDTO for source name '{source['name']}' and target name '{target['name']}'.")
                return PathsNameDTO(source=source['name'], destination=target['name'], requestedCarriers=requested_carriers, validCarriers=[], paths=[])


    def _get_paths_dto(self, 
                      source: ig.Vertex, 
                      target: ig.Vertex, 
                      requested_carriers: List[str], 
                      valid_carriers: List[str],
                      path_prob_list: List[ProbPathIdDTO | ProbPathNameDTO],
                      by: VertexIdentifier) -> PathsIdDTO | PathsNameDTO:
        
        match by:
            case VertexIdentifier.INDEX:
                logger.debug(f"Creating PathsIdDTO for source index {source.index} and target index {target.index}.")
                return PathsIdDTO(source=source.index, destination=target.index, requestedCarriers=requested_carriers, validCarriers=valid_carriers, paths=cast(List[ProbPathIdDTO], path_prob_list))
            
            case VertexIdentifier.ID:
                logger.debug(f"Creating PathsIdDTO for source ID {source[V_ID_ATTR]} and target ID {target[V_ID_ATTR]}.")
                return PathsIdDTO(source=source[V_ID_ATTR], destination=target[V_ID_ATTR], requestedCarriers=requested_carriers, validCarriers=valid_carriers, paths=cast(List[ProbPathIdDTO], path_prob_list))
            
            case VertexIdentifier.NAME:
                logger.debug(f"Creating PathsNameDTO for source name '{source['name']}' and target name '{target['name']}'.")
                return PathsNameDTO(source=source['name'], destination=target['name'], requestedCarriers=requested_carriers, validCarriers=valid_carriers, paths=cast(List[ProbPathNameDTO], path_prob_list))


    def _get_prob_path_dto(self, path: PathIndex, prob: float, carrier: str, by: VertexIdentifier) -> ProbPathIdDTO | ProbPathNameDTO:
        path_resolved: Path = resolve_path(self.graph, path, by)
        match by:
            case VertexIdentifier.INDEX:
                return ProbPathIdDTO(path=cast(PathIndex, path_resolved), prob=prob, carrier=carrier)
            case VertexIdentifier.ID:
                return ProbPathIdDTO(path=cast(PathId, path_resolved), prob=prob, carrier=carrier)
            case VertexIdentifier.NAME:
                return ProbPathNameDTO(path=cast(PathName, path_resolved), prob=prob, carrier=carrier)
            case _:
                raise ValueError(f"Invalid vertex identifier: {by}. Expected one of {list(VertexIdentifier)}.")
        

    def compute_paths_prob(self, 
                           source: Union[int, str, ig.Vertex], 
                           carriers: List[str], 
                           paths: List[PathIndex], 
                           zero_prob_paths: bool = False,
                           by: VertexIdentifier = VertexIdentifier.ID 
                           ) -> PathsIdDTO | PathsNameDTO:
        g: ig.Graph = self.graph
        dp_manager: PathProbDPManager = self.dp_manager
        
        source_v: ig.Vertex = resolve_vertex(g, source)
        source_index: int = source_v.index
        source_id: int = source_v[V_ID_ATTR]
        source_name: str = source_v['name']

        target_v: ig.Vertex = self.manufacturer
        target_index: int = target_v.index
        target_id: int = target_v[V_ID_ATTR]
        target_name: str = target_v['name']

        logger.debug(f"Computing paths probabilities from source vertex {source_name} (ID: {source_id}, index: {source_index})"
                     f" to destination vertex {target_name} (ID: {target_id}, index: {target_index})"
                     f" for requested carriers: {carriers}.")
        
        if not paths:
            logger.debug(f"No paths provided")
            return self._get_empty_paths_dto(source_v, target_v, carriers, by)

        # Validate carriers presence in source vertex orders
        legal_carriers: Set[str] = set(source_v[N_ORDERS_BY_CARRIER_ATTR].keys())
        valid_carriers: Set[str] = self._validate_carriers(carriers, legal_carriers)
        if not valid_carriers:
            logger.debug(f"No valid carriers found in legal carriers: {legal_carriers} for requested carriers: {carriers}.")
            return self._get_empty_paths_dto(source_v, target_v, carriers, by)

        probs_by_valid_carrier: Dict[str, List[float]] = defaultdict(list)
        n_orders_by_valid_carrier: Dict[str, int] = {} 

        for carrier in valid_carriers:
            n_orders_by_valid_carrier[carrier] = source_v[N_ORDERS_BY_CARRIER_ATTR][carrier]
            logger.debug(f"Processing carrier '{carrier}'.")

            if not dp_manager.contains(carrier, source_index):
                logger.debug(f"No cached probability DP for carrier '{carrier}'. Computing probabilities.")

                for path in paths:
                    prob: float = self._compute_path_probability(carrier, path)
                    dp_manager.add(carrier, source_index, prob)
                    logger.debug(f"Computed probability {prob} for path {path} and carrier '{carrier}'.")

            else:
                logger.debug(f"Probability DP cached for carrier '{carrier}' at source vertex; skipping computation.")

            probs_by_valid_carrier[carrier] = dp_manager.get(carrier, source_index)
            logger.debug(f"Retrieved {len(probs_by_valid_carrier[carrier])} probabilities for carrier '{carrier}'.")

        logger.debug(f"Normalizing and aggregating paths for all carriers.")

        total_valid_orders: int = sum(n_orders_by_valid_carrier.values())
        all_prob_paths: List[ProbPathIdDTO | ProbPathNameDTO] = []

        for carrier, probs in probs_by_valid_carrier.items():
            norm_factor: float = n_orders_by_valid_carrier[carrier] / total_valid_orders if total_valid_orders > 0 else 1.0
            for path, prob in zip(paths, probs):
                if prob == 0.0 and not zero_prob_paths:
                    logger.debug(f"Skipping zero-probability path {path} for carrier '{carrier}'.")
                    continue
                    
                prob *= norm_factor
                prob_path_dto: ProbPathIdDTO | ProbPathNameDTO = self._get_prob_path_dto(path, prob, carrier, by)
                all_prob_paths.append(prob_path_dto)
                logger.debug(f"Added probabilistic path {prob_path_dto.path} with probability {prob_path_dto.prob} for carrier '{carrier}'.")


        result: PathsIdDTO | PathsNameDTO = self._get_paths_dto(
            source=source_v,
            target=target_v,
            requested_carriers=carriers,
            valid_carriers=list(valid_carriers),
            path_prob_list=all_prob_paths,
            by=by
        )
        logger.debug(f"Paths extraction complete with total {len(all_prob_paths)} probabilistic paths.")
        return result