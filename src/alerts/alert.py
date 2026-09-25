from dataclasses import dataclass
from datetime import datetime


@dataclass
class Alert:
    camera_id: str
    zone_id: str
    zone_name: str
    previous_status: str | None
    current_status: str
    count: int
    threshold: int
    timestamp: datetime
    alert_type: str
    alert_id: int | None = None
    active: bool = True
    resolved: bool = False