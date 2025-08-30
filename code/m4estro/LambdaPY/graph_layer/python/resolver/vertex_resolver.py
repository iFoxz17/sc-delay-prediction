from typing import Optional, List
from sqlalchemy import func
from dataclasses import dataclass
import igraph as ig

from model.vertex import VertexType
from model.location import Location

from graph_config import V_ID_ATTR, TYPE_ATTR
from service.db_connector import DBConnector
from service.db_utils import get_db_connector
from service.lambda_client.geo_service_lambda_client import GeoServiceLambdaClient, LocationResult

from resolver.vertex_not_found_exception import (
    VertexIdNotFoundException,
    VertexNameNotFoundException,
    VertexNameTypeNotFoundException
)
from resolver.vertex_dto import VertexDTO, VertexIdDTO, VertexNameDTO

from logger import get_logger
logger = get_logger(__name__)

@dataclass
class VertexResult:
    vertex: ig.Vertex

class VertexResolver:
    def __init__(self, graph: ig.Graph, lambda_client: GeoServiceLambdaClient) -> None:
        self.graph: ig.Graph = graph
        self.lambda_client: GeoServiceLambdaClient = lambda_client


    def resolve(self, vertex_dto: VertexDTO) -> VertexResult:
        graph: ig.Graph = self.graph
        logger.debug(f"Resolving vertex for DTO: {vertex_dto}")
        
        if isinstance(vertex_dto, VertexIdDTO):
            logger.debug(f"Resolving by ID: {vertex_dto.vertex_id}")
            vertex: ig.Vertex = self._get_by_id(graph, vertex_dto.vertex_id)
        elif isinstance(vertex_dto, VertexNameDTO):
            logger.debug(f"Resolving by name: {vertex_dto.vertex_name} with type {vertex_dto.vertex_type}")
            vertex: ig.Vertex = self._resolve_by_name(graph, vertex_dto)
        else:
            logger.error("Invalid VertexDTO type")
            raise ValueError("Invalid VertexDTO type")

        logger.debug(f"Vertex resolved: {vertex}")
        return VertexResult(vertex=vertex)

    def _get_by_id(self, graph: ig.Graph, vertex_id: int) -> ig.Vertex:
        try:
            return graph.vs.find(**{V_ID_ATTR: vertex_id})
        except ValueError:
            logger.warning(f"Vertex ID not found: {vertex_id}")
            raise VertexIdNotFoundException(vertex_id)

    def _get_by_name(self, graph: ig.Graph, vertex_name: str) -> ig.Vertex:
        try:
            return graph.vs.find(name=vertex_name)
        except ValueError:
            logger.warning(f"Vertex name not found: {vertex_name}")
            raise VertexNameNotFoundException(vertex_name)

    def _resolve_by_name(self, graph: ig.Graph, dto: VertexNameDTO) -> ig.Vertex:
        maybe_name: Optional[str] = dto.vertex_name
        maybe_type: Optional[VertexType] = dto.vertex_type

        if maybe_name is None:
            if maybe_type == VertexType.MANUFACTURER:
                logger.debug("Resolving manufacturer by type only")
                return graph.vs.find(type=VertexType.MANUFACTURER.value)
            
            logger.error("Vertex name is required for resolution of vertices of type other than MANUFACTURER")
            raise VertexNameNotFoundException("Vertex name is required for resolution of vertices of type other than MANUFACTURER")
            
        name: str = maybe_name
        if maybe_type is None:
            logger.debug("No vertex type provided, resolving by name only")
            return self._get_by_name(graph, name)

        vtype: VertexType = maybe_type
        try:
            match vtype:
                case VertexType.MANUFACTURER:                    
                    logger.debug(f"Resolving manufacturer with name {name}")
                    return graph.vs.find(name=name, **{TYPE_ATTR: VertexType.MANUFACTURER.value})

                case VertexType.SUPPLIER_SITE:
                    logger.debug(f"Resolving supplier site with name {name}")
                    return graph.vs.find(name=name, **{TYPE_ATTR: VertexType.SUPPLIER_SITE.value})

                case VertexType.INTERMEDIATE:
                    logger.debug(f"Resolving intermediate with name {name}")
                    return self._resolve_intermediate_vertex(graph, name)

                case _:
                    logger.error(f"Unsupported vertex type: {vtype}. This should never happen.")
                    raise VertexNameTypeNotFoundException(name, vtype.value)
        
        except ValueError:
            logger.warning(f"Vertex with name {name} and type {vtype} not found")
            raise VertexNameTypeNotFoundException(name, vtype.value)

    def _resolve_intermediate_vertex(self, graph: ig.Graph, vertex_name: str) -> ig.Vertex:
        try:
            return graph.vs.find(name=vertex_name, **{TYPE_ATTR: VertexType.INTERMEDIATE.value})
        except ValueError:
            logger.debug(f"Initial lookup failed for intermediate vertex: {vertex_name}")

        parts: List[str] = [p.strip() for p in vertex_name.split(",")]
        logger.debug(f"Split vertex name into parts: {parts}")
        if len(parts) == 0:
            logger.error(f"Invalid vertex name format: {vertex_name}")
            raise VertexNameTypeNotFoundException(vertex_name, VertexType.INTERMEDIATE.value)
        
        if len(parts) == 1:
            city, country = parts[0], None
        else:
            city, country = parts[0], parts[2] if len(parts) > 2 else parts[1]
        
        logger.debug(f"Resolving location: city={city}, country={country}")
        connector: DBConnector = get_db_connector()

        maybe_location: Optional[Location] = self._lookup_location_in_db(connector, city, country)
        if maybe_location:
            location: Location = maybe_location
        else:
            logger.debug(f"Location not found in DB, calling external API")
            location: Location = self._lookup_location_via_api(connector, city, country)
            
        unified_name: str = location.name
        logger.debug(f"Unified location name: {unified_name}")

        try:
            return graph.vs.find(name=unified_name, **{TYPE_ATTR: VertexType.INTERMEDIATE.value})
        except ValueError:
            logger.warning(f"Vertex not found with unified name: {unified_name}")
            raise VertexNameTypeNotFoundException(vertex_name, VertexType.INTERMEDIATE.value)

    def _lookup_location_in_db(self, connector: DBConnector, city: str, maybe_country_code: Optional[str]) -> Optional[Location]:
        logger.debug(f"Looking up location in DB: city={city}, country_code={maybe_country_code}")
        with connector.session_scope() as session:
            query = session.query(Location).filter(func.upper(Location.city) == city)

            if maybe_country_code:
                country_code: str = maybe_country_code
                logger.debug(f"Filtering by city and country code")
                query = query.filter(func.upper(Location.country_code) == country_code)
            else:
                logger.debug(f"Filtering by city only, no country code provided")

            maybe_locations: List[Location] = query.all()

        if len(maybe_locations) == 0:
            logger.debug(f"No locations found in DB for city={city}, country_code={maybe_country_code}")
            return None
        if len(maybe_locations) == 1:
            logger.debug(f"Found single location in DB: {maybe_locations[0]}")
            return maybe_locations[0]
        else:
            logger.warning(f"Multiple locations found in DB for city={city}, country_code={maybe_country_code}: {maybe_locations}")
            return None

    def _lookup_location_via_api(self, connector: DBConnector, city: str, maybe_country: Optional[str]) -> Location:
        country: str = maybe_country or ""
        try:
            result: LocationResult = self.lambda_client.get_location_data(city=city, country=country)
        except Exception as e:
            raise VertexNameTypeNotFoundException(f"{city}, {country}", VertexType.INTERMEDIATE.value) from e

        location: Location = Location(
            name=result.name,
            city=result.city,
            state=result.state,
            country_code=result.country_code,
            latitude=result.latitude,
            longitude=result.longitude
        )
        
        with connector.session_scope() as session:
            maybe_existing_location: Optional[Location] = session.query(Location).filter(
                Location.name == location.name,
            ).first()
            if maybe_existing_location:
                location: Location = maybe_existing_location
                logger.debug(f"Location already existing in DB: {location}")
            else:
                logger.debug(f"Adding new location to DB: {location}")
                session.add(location)
                session.commit()
        
        return location

