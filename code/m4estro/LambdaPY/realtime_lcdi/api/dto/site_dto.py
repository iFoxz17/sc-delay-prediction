from pydantic import BaseModel, Field, ConfigDict

class SiteIdDTO(BaseModel):
    site_id: int = Field(
        ..., 
        alias="siteId",
        description="Unique identifier for the site."
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

SiteDTO = SiteIdDTO
