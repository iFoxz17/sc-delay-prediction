from typing import List, Tuple, TYPE_CHECKING
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import igraph as ig

from model.vertex import VertexType

from graph_config import (
    V_ID_ATTR,
    TYPE_ATTR,
    LATITUDE_ATTR,
    LONGITUDE_ATTR,
    AVG_ORI_ATTR,
    DISTANCE_ATTR,
    AVG_OTI_ATTR,
    AVG_WMI_ATTR,
    AVG_TMI_ATTR,
)

from core.calculator.tfst.pt.vertex_time.vertex_time_input_dto import VertexTimeInputDTO
from core.calculator.tfst.pt.route_time.route_time_input_dto import RouteTimeInputDTO

from core.dto.path.paths_dto import PathsIdDTO
from core.dto.path.prob_path_dto import ProbPathIdDTO
from core.dto.path.prob_path_time_dto import ProbPathIdTimeDTO

from core.calculator.tfst.pt.tmi.tmi_dto import TMIInputDTO
from core.calculator.tfst.pt.wmi.wmi_dto import WMIInputDTO

from core.calculator.tfst.pt.pt_dto import PT_DTO

from core.sc_graph.utils import VertexIdentifier

if TYPE_CHECKING:
    from core.dto.time_sequence.time_sequence_dto import TimeSequenceDTO
    
    from core.query_handler.params.params_result import PTParams

    from core.sc_graph.sc_graph import SCGraph
    from core.calculator.tfst.pt.vertex_time.vertex_time_dto import VertexTimeDTO
    from core.calculator.tfst.pt.vertex_time.vertex_time_calculator import VertexTimeCalculator

    from core.calculator.tfst.pt.route_time.route_time_dto import RouteTimeDTO
    from core.calculator.tfst.pt.route_time.route_time_calculator import RouteTimeCalculator

    from core.calculator.tfst.pt.tmi.tmi_manager import TMIManager
    from core.calculator.tfst.pt.tmi.tmi_dto import TMIValueDTO
    
    from core.calculator.tfst.pt.wmi.wmi_manager import WMIManager
    from core.calculator.tfst.pt.wmi.wmi_dto import WMIValueDTO

    from core.dto.path.paths_dto import PathsNameDTO
    from core.calculator.tfst.pt.pt_input_dto import PTInputDTO
    
from logger import get_logger
logger = get_logger(__name__)

class PTCalculator:
    def __init__(self, 
                 sc_graph: 'SCGraph',
                 vt_calculator: 'VertexTimeCalculator',
                 rt_calculator: 'RouteTimeCalculator', 
                 tmi_manager: 'TMIManager',
                 wmi_manager: 'WMIManager',
                 params: 'PTParams'
                 ) -> None:
        
        self.sc_graph: 'SCGraph' = sc_graph

        self.vt_calculator: 'VertexTimeCalculator' = vt_calculator
        self.rt_calculator: 'RouteTimeCalculator' = rt_calculator
        
        self.tmi_manager: 'TMIManager' = tmi_manager
        self.wmi_manager: 'WMIManager' = wmi_manager
        
        self.params: 'PTParams' = params
        
    def _compute_tmi(self, 
                     prob: float,
                     s: 'ig.Vertex', 
                     d: 'ig.Vertex', 
                     route_distance: float,
                     route_average_time: float, 
                     estimation_time: datetime, 
                     current_time: datetime) -> 'TMIValueDTO':
        if prob < self.params.ext_data_min_probability:
            logger.debug(f"Probability = {prob} < {self.params.ext_data_min_probability}, skipping TMI calculation")
            return TMIValueDTO(value=0.0, computed=False)

        tmi_input: TMIInputDTO = TMIInputDTO(
            source=s,
            destination=d,
            route_geodesic_distance=route_distance,
            route_average_time=route_average_time,
            shipment_estimation_time=estimation_time,
            departure_time=current_time
        )
        return self.tmi_manager.calculate_tmi(tmi_input)
    
    def _compute_wmi(self, 
                     prob: float,
                     s: 'ig.Vertex', 
                     d: 'ig.Vertex', 
                     route_average_time: float, 
                     estimation_time: datetime, 
                     current_time: datetime) -> 'WMIValueDTO':
        ext_data_min_prob: float = self.params.ext_data_min_probability
        if prob < ext_data_min_prob:
            logger.debug(f"Probability = {prob} < {ext_data_min_prob}, skipping WMI calculation")
            return WMIValueDTO(value=0.0, computed=False)

        wmi_input: WMIInputDTO = WMIInputDTO(
            source=s,
            destination=d,
            route_average_time=route_average_time,
            shipment_estimation_time=estimation_time,
            departure_time=current_time
        )
        return self.wmi_manager.calculate_wmi(wmi_input)


    def _calculate_vertex_time(self, v: ig.Vertex, event_time: datetime, current_time: datetime, first_vertex: bool = False) -> Tuple[float, float]:
        if v[TYPE_ATTR] in {VertexType.MANUFACTURER.value, VertexType.SUPPLIER_SITE.value}:
            logger.debug("Skipping vertex time calculation for type '%s'", v[TYPE_ATTR])
            return 0.0, 0.0
        
        vti: VertexTimeInputDTO = VertexTimeInputDTO(avg_ori=v[AVG_ORI_ATTR])
        v_time: 'VertexTimeDTO' = self.vt_calculator.calculate(vti, self.params.confidence)
        l, u = v_time.lower, v_time.upper
        logger.debug(f"Vertex time for vertex {v[V_ID_ATTR]} ({v['name']}) at {current_time}: lower={l}, upper={u}")

        if first_vertex:
            elapsed_hours: float = (current_time - event_time).total_seconds() / 3600.0
            l: float = max(l - elapsed_hours, 0.0) 
            u: float = max(u - elapsed_hours, 0.0)
            logger.debug(f"First vertex remaining time adjustment: elapsed={elapsed_hours}, lower={l}, upper={u}")

        return l, u
    
    def _calculate_route_time(self, s: ig.Vertex, d: ig.Vertex, e: ig.Edge, tmi: 'TMIValueDTO', wmi: 'WMIValueDTO', current_time: datetime) -> Tuple[float, float]:
        rti: RouteTimeInputDTO = RouteTimeInputDTO(
            latitude_source=s[LATITUDE_ATTR],
            longitude_source=s[LONGITUDE_ATTR],
            latitude_destination=d[LATITUDE_ATTR],
            longitude_destination=d[LONGITUDE_ATTR],
            distance=e[DISTANCE_ATTR],
            avg_oti=e[AVG_OTI_ATTR],
            tmi=tmi,
            avg_wmi=e[AVG_WMI_ATTR],
            wmi=wmi,
            avg_tmi=e[AVG_TMI_ATTR],
        )
        r_time: 'RouteTimeDTO' = self.rt_calculator.calculate(rti, self.params.confidence)
        logger.debug(f"Route time for edge ({s[V_ID_ATTR]} -> {d[V_ID_ATTR]}) at {current_time}: lower={r_time.lower}, upper={r_time.upper}")
        
        return r_time.lower, r_time.upper

    def _calculate_path_time(self, path: List[int], prob: float, event_time: datetime, estimation_time: datetime) -> Tuple[float, float, float, float]:
        g: ig.Graph = self.sc_graph.graph
        l_time, u_time = 0.0, 0.0
        starting_tmi, starting_wmi = 0.0, 0.0
        current_time: datetime = estimation_time

        for i in range(len(path) - 1):
            s_id: int = path[i]
            d_id: int = path[i + 1]
            
            s: ig.Vertex = g.vs.find(**{V_ID_ATTR: s_id})
            d: ig.Vertex = g.vs.find(**{V_ID_ATTR: d_id})
            e: ig.Edge = g.es[g.get_eid(s, d)]

            l, u = self._calculate_vertex_time(s, event_time, current_time, first_vertex=(i == 0))
            
            l_time += l
            u_time += u
            current_time += timedelta(hours=(l + u) / 2.0)

            tmi: 'TMIValueDTO' = self._compute_tmi(prob, s, d, e[DISTANCE_ATTR], e[AVG_OTI_ATTR], estimation_time, current_time)
            if i == 0:
                starting_tmi: float = tmi.value
                logger.debug(f"Starting TMI for first route ({s_id} -> {d_id}) at time {current_time}: {starting_tmi}")

            wmi: 'WMIValueDTO' = self._compute_wmi(prob, s, d, e[AVG_OTI_ATTR], estimation_time, current_time)
            if i == 0:
                starting_wmi: float = wmi.value
                logger.debug(f"Starting WMI for first route ({s_id} -> {d_id}) at time {current_time}: {starting_wmi}")

            l, u = self._calculate_route_time(s, d, e, tmi, wmi, current_time)
            
            l_time += l
            u_time += u
            current_time += timedelta(hours=(l + u) / 2.0)

        last_vertex: ig.Vertex = g.vs.find(**{V_ID_ATTR: path[-1]})
        l, u = self._calculate_vertex_time(last_vertex, event_time, current_time, first_vertex=(len(path) == 1))

        l_time += l
        u_time += u

        return l_time, u_time, starting_tmi, starting_wmi
    
    def _handle_path_time_failure(self, successful_paths: List[ProbPathIdTimeDTO], failed_paths: List[ProbPathIdDTO]) -> None:
        if not successful_paths:
            return

        logger.debug(f"Adjusting probabilities for {len(successful_paths)} successful paths")
        
        failed_prob: float = sum(p.prob for p in failed_paths)
        logger.debug(f"Total failed probability: {failed_prob:.4f}")

        for p in successful_paths:
            adjusted_prob: float = p.prob / (1.0 - failed_prob)
            logger.debug(f"Adjusted probability for {p.path}: {p.prob} -> {adjusted_prob}")
            p.prob = adjusted_prob

    def empty_path_dto(self) -> PT_DTO:
        return PT_DTO(
            lower=0.0, upper=0.0,
            n_paths=0, avg_tmi=0.0, avg_wmi=0.0,
            params=self.params,
            tmi_data=[],
            wmi_data=[]
        )

    def calculate_remaining_time(self, pt_input: 'PTInputDTO', event_time: datetime, estimation_time: datetime) -> PT_DTO:
        path_min_prob: float = self.params.path_min_probability
        max_paths: int = self.params.max_paths
        
        sc_graph: 'SCGraph' = self.sc_graph    
        v_id: int = pt_input.vertex_id
        try:
            vertex: ig.Vertex = sc_graph.graph.vs.find(**{V_ID_ATTR: v_id})
        except Exception:
            logger.exception(f"Vertex with ID {v_id} not found in the graph")
            raise ValueError(f"Vertex with ID {v_id} not found in the graph")
        
        logger.debug(f"Extracting paths for vertex {v_id} ({vertex["name"]}) and carriers {pt_input.carrier_names})")
        all_paths_dto: 'PathsIdDTO | PathsNameDTO' = self.sc_graph.extract_paths(vertex, pt_input.carrier_names, zero_prob_paths=False, by=VertexIdentifier.ID)
        if not isinstance(all_paths_dto, PathsIdDTO):
            logger.error(f"Expected PathsIdDTO, but got {type(all_paths_dto)}: this should never happen.")
            raise TypeError(f"Expected PathsIdDTO, but got {type(all_paths_dto)}: this should never happen.")
        all_paths: List[ProbPathIdDTO] = all_paths_dto.paths

        logger.debug(f"Extracted {len(all_paths)} paths from the graph with non-zero probability: {all_paths}")

        filtered_paths: List[ProbPathIdDTO] = [path for path in all_paths if path.prob >= path_min_prob]
        if not filtered_paths:
            logger.warning(f"No paths found with probability >= {path_min_prob}, returning default PT_DTO")
            return self.empty_path_dto()

        logger.debug(f"Filtered {len(filtered_paths)} paths with probability >= {path_min_prob}")

        if len(filtered_paths) > max_paths:
            filtered_paths = sorted(filtered_paths, key=lambda p: p.prob, reverse=True)[:max_paths]
            logger.debug(f"Filtered {max_paths} paths with highest probabilities")

        if len(filtered_paths) < len(all_paths):
            filtered_prob: float = sum(p.prob for p in filtered_paths)
            for p in filtered_paths:
                p.prob /= filtered_prob

            logger.debug("Normalized path filtered paths probabilities")

        paths: PathsIdDTO = PathsIdDTO(
            source=all_paths_dto.source,
            destination=all_paths_dto.destination,
            requestedCarriers=pt_input.carrier_names,
            validCarriers=all_paths_dto.valid_carriers,
            paths=filtered_paths,
        )
        logger.debug(f"Filtered {len(paths.paths)} paths with non-zero probability: {paths}")

        logger.debug(f"Calculating PT for {len(paths.paths)} paths with event_time={event_time} and estimation_time={estimation_time}")

        successful_paths: List[ProbPathIdTimeDTO] = []
        failed_paths: List[ProbPathIdDTO] = []
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self._calculate_path_time, path_prob.path, path_prob.prob, event_time, estimation_time): path_prob
                for path_prob in paths.paths
            }

            for f in as_completed(futures):
                path_prob: ProbPathIdDTO = futures[f]
                try:
                    l_time, u_time, starting_tmi, starting_wmi = f.result()
                    path_prob_time: ProbPathIdTimeDTO = ProbPathIdTimeDTO(
                        path=path_prob.path,
                        prob=path_prob.prob,
                        lower_time=l_time,
                        upper_time=u_time,
                        avg_tmi=starting_tmi,
                        avg_wmi=starting_wmi,
                        carrier=path_prob.carrier,
                    )

                    successful_paths.append(path_prob_time)
                    logger.debug(f"PT calculated for path {path_prob.path}: "
                                 f"prob={path_prob.prob}, lower_time={l_time}, upper_time={u_time}, "
                                 f"avg_tmi={starting_tmi}, avg_wmi={starting_wmi}")
                except Exception:
                    logger.exception(f"Failed to calculate PT for path {path_prob.path} with probability {path_prob.prob}")
                    failed_paths.append(path_prob)

        logger.debug(f"PT successfully calculated for {len(successful_paths)} paths, failed for {len(failed_paths)} paths")
        
        if failed_paths:
            logger.debug(f"Starting failure handling for {len(failed_paths)} failed paths")
            self._handle_path_time_failure(successful_paths, failed_paths)
            if not successful_paths:
                logger.warning("No successful paths remaining after failure handling")
                return self.empty_path_dto()

        probs: List[float] = [p.prob for p in successful_paths]
        l_times: List[float] = [p.lower_time for p in successful_paths]
        u_times: List[float] = [p.upper_time for p in successful_paths]
        tmis: List[float] = [p.avg_tmi for p in successful_paths]
        wmis: List[float] = [p.avg_wmi for p in successful_paths]

        lower: float = np.dot(probs, l_times)
        upper: float = np.dot(probs, u_times)
        avg_tmi: float = np.dot(probs, tmis)
        avg_wmi: float = np.dot(probs, wmis)

        return PT_DTO(
            lower=lower, upper=upper,
            n_paths=len(successful_paths), avg_tmi=avg_tmi, avg_wmi=avg_wmi,
            params=self.params
        )

    def calculate(self, pt_input: 'PTInputDTO', time_sequence: 'TimeSequenceDTO') -> PT_DTO:
        tmi_manager: 'TMIManager' = self.tmi_manager
        tmi_manager.initialize()

        event_time: datetime = time_sequence.shipment_event_time
        estimation_time: datetime = time_sequence.shipment_estimation_time

        pt_remaining_time: PT_DTO = self.calculate_remaining_time(pt_input, event_time, estimation_time)
        remaining_l: float = pt_remaining_time.lower
        remaining_u: float = pt_remaining_time.upper

        elapsed: float = (estimation_time - time_sequence.shipment_time).total_seconds() / 3600.0
        total_l: float = elapsed + remaining_l
        total_u: float = elapsed + remaining_u
 
        logger.debug(f"PT computed with params={self.params}: "
                     f"total_time=[{total_l}, {total_u}], "
                     f"elapsed_time={elapsed}, "
                     f"remaining_time=[{remaining_l}, {remaining_u}]")
        
        return PT_DTO(
            lower=remaining_l, 
            upper=remaining_u,
            n_paths=pt_remaining_time.n_paths,
            avg_wmi=pt_remaining_time.avg_wmi,
            avg_tmi=pt_remaining_time.avg_tmi,
            params=self.params,
            tmi_data=tmi_manager.tmi_data,
            wmi_data=self.wmi_manager.wmi_data
        )