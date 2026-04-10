from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PipelineMode(str, Enum):
    FAST = "fast"
    FULL = "full"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class VisualClues(BaseModel):
    text_and_signage: dict = Field(default_factory=dict)
    architecture: dict = Field(default_factory=dict)
    infrastructure: dict = Field(default_factory=dict)
    nature: dict = Field(default_factory=dict)
    environmental: dict = Field(default_factory=dict)
    vehicles_and_people: dict = Field(default_factory=dict)
    distinctive_features: dict = Field(default_factory=dict)
    overall_impression: str = ""


class Hypothesis(BaseModel):
    rank: int
    country: str
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: float
    longitude: float
    confidence_pct: float = Field(ge=0, le=100)
    reasoning: str
    confirming_evidence: list[str] = Field(default_factory=list)
    refuting_evidence: list[str] = Field(default_factory=list)


class ToolResult(BaseModel):
    tool_name: str
    hypothesis_rank: int
    supports: bool
    confidence_delta: float = Field(ge=-30, le=30)
    evidence_summary: str
    raw_data: Optional[dict] = None


class ExifData(BaseModel):
    has_gps: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    datetime_original: Optional[str] = None
    orientation: Optional[int] = None


class GeoResult(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None
    country: str
    region: Optional[str] = None
    city: Optional[str] = None
    confidence: Confidence
    confidence_pct: float
    reasoning_trace: str
    clues_used: VisualClues
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    tool_evidence: list[ToolResult] = Field(default_factory=list)
