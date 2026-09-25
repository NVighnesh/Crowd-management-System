from dataclasses import dataclass


@dataclass
class Detection:
    class_id: int
    confidence: float
    bbox: tuple[int, int, int, int]
    track_id: int | None = None