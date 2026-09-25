from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ZoneResult:

    zone_id: str

    name: str

    count: int

    threshold: int

    status: str


@dataclass
class CrowdAnalysisResult:

    camera_id: str

    total_people: int | None

    zones: list[ZoneResult] = field(
        default_factory=list
    )

    timestamp: datetime | None = None