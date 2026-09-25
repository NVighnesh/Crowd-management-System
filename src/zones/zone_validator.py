import json
import math

from src.config.settings import resolve_path


class ZoneValidator:

    @staticmethod
    def validate_file(
        config_path: str,
        expected_camera_id: str | None = None,
    ):

        path = resolve_path(config_path)

        if not path.exists():
            raise ValueError(
                f"Zone configuration not found: {path}"
            )

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        ZoneValidator.validate(
            data,
            expected_camera_id,
        )

        return True

    @staticmethod
    def validate(
        data,
        expected_camera_id: str | None = None,
    ):

        if not isinstance(data, dict):
            raise ValueError(
                "Zone configuration must be a JSON object."
            )

        if "camera_id" not in data:
            raise ValueError(
                "Zone configuration is missing 'camera_id'."
            )

        if "zones" not in data:
            raise ValueError(
                "Zone configuration is missing 'zones'."
            )

        camera_id = data["camera_id"]

        if not isinstance(
            camera_id,
            str,
        ) or not camera_id:

            raise ValueError(
                "'camera_id' must be a non-empty string."
            )

        if (
            expected_camera_id is not None
            and camera_id != expected_camera_id
        ):

            raise ValueError(
                f"Zone configuration belongs to "
                f"{camera_id}, but camera "
                f"{expected_camera_id} was expected."
            )

        zones = data["zones"]

        if not isinstance(
            zones,
            list,
        ):

            raise ValueError(
                "'zones' must be a list."
            )

        if not zones:

            raise ValueError(
                f"No zones configured for camera "
                f"{camera_id}."
            )

        zone_ids = set()

        for zone in zones:

            if not isinstance(
                zone,
                dict,
            ):

                raise ValueError(
                    "Each zone must be a JSON object."
                )

            required_fields = [
                "zone_id",
                "camera_id",
                "name",
                "threshold",
                "threshold_type",
                "polygon",
            ]

            for field in required_fields:

                if field not in zone:

                    raise ValueError(
                        f"Zone configuration is missing "
                        f"'{field}'."
                    )

            zone_id = zone["zone_id"]

            if (
                not isinstance(
                    zone_id,
                    str,
                )
                or not zone_id
            ):

                raise ValueError(
                    "'zone_id' must be a non-empty string."
                )

            if zone_id in zone_ids:

                raise ValueError(
                    f"Duplicate zone ID: {zone_id}"
                )

            zone_ids.add(zone_id)

            if zone["camera_id"] != camera_id:

                raise ValueError(
                    f"Zone {zone_id} belongs to "
                    f"{zone['camera_id']}, but the "
                    f"zone file belongs to "
                    f"{camera_id}."
                )

            if (
                not isinstance(
                    zone["name"],
                    str,
                )
                or not zone["name"]
            ):

                raise ValueError(
                    f"Zone {zone_id} must have "
                    f"a non-empty name."
                )

            threshold = zone["threshold"]

            if (
                not isinstance(
                    threshold,
                    (int, float),
                )
                or isinstance(
                    threshold,
                    bool,
                )
                or threshold < 0
            ):

                raise ValueError(
                    f"Zone {zone_id} has an invalid "
                    f"threshold: {threshold}"
                )

            threshold_type = zone[
                "threshold_type"
            ]

            if threshold_type != "count":

                raise ValueError(
                    f"Unsupported threshold_type "
                    f"'{threshold_type}' in zone "
                    f"{zone_id}."
                )

            polygon = zone["polygon"]

            if not isinstance(
                polygon,
                list,
            ):

                raise ValueError(
                    f"Polygon for zone {zone_id} "
                    f"must be a list."
                )

            if len(polygon) < 3:

                raise ValueError(
                    f"Polygon for zone {zone_id} "
                    f"must contain at least "
                    f"3 points."
                )

            # Validate every polygon point.
            for point in polygon:

                if (
                    not isinstance(
                        point,
                        list,
                    )
                    or len(point) != 2
                ):

                    raise ValueError(
                        f"Invalid polygon point "
                        f"in zone {zone_id}: "
                        f"{point}"
                    )

                x, y = point

                if (
                    not isinstance(
                        x,
                        (int, float),
                    )
                    or isinstance(
                        x,
                        bool,
                    )
                    or not isinstance(
                        y,
                        (int, float),
                    )
                    or isinstance(
                        y,
                        bool,
                    )
                ):

                    raise ValueError(
                        f"Polygon coordinates for "
                        f"zone {zone_id} must be "
                        f"numbers."
                    )

                if not (
                    math.isfinite(x)
                    and math.isfinite(y)
                ):

                    raise ValueError(
                        f"Polygon coordinates for "
                        f"zone {zone_id} must be finite."
                    )

            # Calculate polygon area using
            # the shoelace formula.
            area = 0.0

            for index in range(len(polygon)):

                x1, y1 = polygon[index]

                x2, y2 = polygon[
                    (index + 1) % len(polygon)
                ]

                area += (
                    x1 * y2
                    - x2 * y1
                )

            area = abs(area) / 2.0

            if area <= 0:

                raise ValueError(
                    f"Polygon for zone {zone_id} "
                    f"has zero area."
                )

        return True
    
    @staticmethod
    def validate_against_frame(
        zones,
        frame_width: int,
        frame_height: int,
    ):
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError(
                "Frame width and height must be positive."
            )

        for zone in zones:

            zone_id = zone["zone_id"]
            polygon = zone["polygon"]

            for x, y in polygon:

                if not (
                    0 <= x < frame_width
                    and 0 <= y < frame_height
                ):
                    raise ValueError(
                        f"Zone {zone_id} contains "
                        f"point ({x}, {y}) outside "
                        f"frame boundaries "
                        f"{frame_width}x{frame_height}."
                    )

        return True