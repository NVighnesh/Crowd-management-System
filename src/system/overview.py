from dataclasses import dataclass, field


@dataclass
class SystemOverview:

    total_cameras: int
    online_cameras: int
    offline_cameras: int
    stale_cameras: int
    total_people: int
    total_alerts: int

    cameras: list[dict] = field(
        default_factory=list
    )

    alerts: list[dict] = field(
        default_factory=list
    )