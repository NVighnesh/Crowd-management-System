import json

from src.config.settings import resolve_path
from src.zones.zone_validator import ZoneValidator


class ZoneManager:
    def __init__(self, config_source, expected_camera_id=None):
        self.config_source = config_source
        self.expected_camera_id = expected_camera_id
        self.camera_id = None
        self.zones = []

    def load(self):
        if isinstance(self.config_source, list):
            data = {
                "camera_id": self.expected_camera_id,
                "zones": self.config_source,
            }
        else:
            config_path = str(self.config_source)

            ZoneValidator.validate_file(
                config_path=config_path,
                expected_camera_id=self.expected_camera_id,
            )

            path = resolve_path(config_path)

            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

        self.camera_id = data.get(
            "camera_id",
            self.expected_camera_id,
        )

        if (
            self.expected_camera_id is not None
            and self.camera_id != self.expected_camera_id
        ):
            raise ValueError(
                f"Zone configuration belongs to "
                f"{self.camera_id}, but camera "
                f"{self.expected_camera_id} was expected."
            )

        self.zones = []

        for zone in data.get("zones", []):
            self.zones.append(
                {
                    "zone_id": zone["zone_id"],
                    "camera_id": zone.get(
                        "camera_id",
                        self.camera_id,
                    ),
                    "name": zone.get(
                        "name",
                        zone.get(
                            "zone_name",
                            zone["zone_id"],
                        ),
                    ),
                    "zone_name": zone.get(
                        "zone_name",
                        zone.get(
                            "name",
                            zone["zone_id"],
                        ),
                    ),
                    "threshold": int(
                        zone.get("threshold", 0)
                    ),
                    "threshold_type": zone.get(
                        "threshold_type",
                        "count",
                    ),
                    "polygon": zone.get(
                        "polygon",
                        [],
                    ),
                    "point": zone.get(
                        "point",
                        "bottom_center",
                    ),
                    "enabled": bool(
                        zone.get("enabled", True)
                    ),
                }
            )

    def get_zones(self):
        return [
            zone
            for zone in self.zones
            if zone.get("enabled", True)
        ]

    def get_zone(self, zone_id):
        for zone in self.zones:
            if zone["zone_id"] == zone_id:
                return zone

        return None

    def get_camera_id(self):
        return self.camera_id

    def reload(self):
        self.load()

    def validate_against_frame(
        self,
        frame_width,
        frame_height,
    ):
        for zone in self.get_zones():
            polygon = zone.get("polygon", [])

            if len(polygon) < 3:
                raise ValueError(
                    f"Zone '{zone['zone_id']}' "
                    f"must contain at least 3 polygon points."
                )

            for point in polygon:
                if len(point) != 2:
                    raise ValueError(
                        f"Zone '{zone['zone_id']}' "
                        f"contains an invalid polygon point."
                    )

                x, y = point

                if (
                    x < 0
                    or x > frame_width
                    or y < 0
                    or y > frame_height
                ):
                    raise ValueError(
                        f"Zone '{zone['zone_id']}' "
                        f"contains a point outside the frame: "
                        f"({x}, {y})"
                    )