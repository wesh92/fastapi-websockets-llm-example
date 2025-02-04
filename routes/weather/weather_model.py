from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re



class QueryMetrics(BaseModel):
    """Metrics about the query execution."""

    query_time_ms: float
    total_records: int

class IncomingWeatherAlertQuery(BaseModel):
    """Query parameters for fetching weather alerts."""
    state: str = Field(
        description="State abbreviation for the alerts",
        example="TN",
    )
    
    @field_validator("state")
    def validate_state(cls, value):
        if not re.match(r"^[A-Z]{2}$", value):
            raise ValueError("State must be a two-letter abbreviation")
        return value

# Breaking the nested structure of the response into separate models
class GeocodeModel(BaseModel):
    """Geographical coding information using SAME and UGC standards."""
    SAME: List[str] = Field(description="Specific Area Message Encoding identifiers")
    UGC: List[str] = Field(description="Universal Geographic Code identifiers")

class AlertParameters(BaseModel):
    """Additional alert parameters and identifiers."""
    AWIPSidentifier: List[str] = Field(description="AWIPS (Advanced Weather Interactive Processing System) identifier")
    WMOidentifier: List[str] = Field(description="World Meteorological Organization identifier")
    NWSheadline: List[str] = Field(description="National Weather Service headline")
    BLOCKCHANNEL: List[str] = Field(description="Blocked distribution channels")
    EAS_ORG: List[str] = Field(alias="EAS-ORG", description="Emergency Alert System organization")

class AlertProperties(BaseModel):
    """Core properties of a weather alert."""
    id: str = Field(description="Unique identifier for the alert")
    areaDesc: str = Field(description="Textual description of affected areas")
    geocode: GeocodeModel = Field(description="Geographical coding information")
    affectedZones: List[str] = Field(description="URLs of affected forecast zones")
    references: List[str] = Field(description="Related alert references")
    
    # Temporal fields
    sent: datetime = Field(description="Time alert was sent")
    effective: datetime = Field(description="Time alert becomes effective")
    onset: datetime = Field(description="Time alert condition begins")
    expires: datetime = Field(description="Time alert expires")
    ends: Optional[datetime] = Field(None, description="Time alert condition ends")
    
    # Alert classification fields
    status: str = Field(description="Alert status (e.g., 'Actual')")
    messageType: str = Field(description="Type of message")
    category: str = Field(description="Alert category")
    severity: str = Field(description="Alert severity level")
    certainty: str = Field(description="Certainty of alert condition")
    urgency: str = Field(description="Urgency of alert")
    event: str = Field(description="Type of weather event")
    
    # Source and content fields
    sender: str = Field(description="Email of alert sender")
    senderName: str = Field(description="Name of sending organization")
    headline: str = Field(description="Alert headline")
    description: str = Field(description="Detailed description of the alert")
    instruction: Optional[str] = Field(None, description="Public action instructions")
    response: str = Field(description="Type of response recommended")
    parameters: AlertParameters = Field(description="Additional alert parameters")

class AlertFeature(BaseModel):
    """Individual weather alert feature."""
    id: str = Field(description="Feature identifier URL")
    type: str = Field(description="GeoJSON feature type")
    geometry: Optional[dict] = Field(None, description="GeoJSON geometry object")
    properties: AlertProperties = Field(description="Alert properties")

class WeatherAlertResponse(BaseModel):
    """Top-level weather alert response model."""
    features: List[AlertFeature] = Field(description="List of weather alert features")
    query_metrics: QueryMetrics = Field(description="Query execution metrics")