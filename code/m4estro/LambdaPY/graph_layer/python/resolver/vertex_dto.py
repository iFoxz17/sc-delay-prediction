from typing import Union, Optional
from pydantic import BaseModel, Field, ConfigDict

from model.vertex import VertexType

class VertexIdDTO(BaseModel):
    vertex_id: int = Field(
        ..., 
        alias="vertexId",
        description="Unique identifier for the vertex in the graph."
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

class VertexNameDTO(BaseModel):
    vertex_name: Optional[str] = Field(
        default=None, 
        alias="vertexName",
        description="Name for the vertex in the graph"
    )

    vertex_type: Optional[VertexType] = Field( 
        default=None,
        alias="vertexType",
        description="Type attribute for the vertex in the graph"
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

VertexDTO = Union[VertexIdDTO, VertexNameDTO]
