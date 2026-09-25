from datetime import datetime, timezone

from src.alerts.alert import Alert


class AlertEngine:

    def __init__(self):

        # --------------------------------------------------
        # Stores the previous status of each zone
        #
        # Key:
        #     (camera_id, zone_id)
        #
        # Value:
        #     previous status
        # --------------------------------------------------

        self._previous_status = {}

    # --------------------------------------------------
    # Evaluate zone status
    # --------------------------------------------------

    def evaluate(
        self,
        camera_id: str,
        zone_id: str,
        zone_name: str,
        current_status: str,
        count: int,
        threshold: int,
    ):

        key = (
            camera_id,
            zone_id,
        )

        previous_status = (
            self._previous_status.get(key)
        )

        # --------------------------------------------------
        # Save current status
        # --------------------------------------------------

        self._previous_status[key] = (
            current_status
        )

        # --------------------------------------------------
        # First observation
        #
        # Do not generate an alert just because
        # the system started while a zone is already
        # RED or YELLOW.
        # --------------------------------------------------

        if previous_status is None:

            return None

        # --------------------------------------------------
        # No status change
        #
        # Example:
        #
        # RED → RED
        #
        # No duplicate alert.
        # --------------------------------------------------

        if previous_status == current_status:

            return None

        # --------------------------------------------------
        # GREEN → YELLOW
        # --------------------------------------------------

        if (
            previous_status == "GREEN"
            and current_status == "YELLOW"
        ):

            return Alert(
                camera_id=camera_id,
                zone_id=zone_id,
                zone_name=zone_name,
                previous_status=previous_status,
                current_status=current_status,
                count=count,
                threshold=threshold,
                timestamp=datetime.now(
                    timezone.utc
                ),
                alert_type="THRESHOLD_REACHED",
                active=True,
            )

        # --------------------------------------------------
        # GREEN → RED
        #
        # This can happen if the count jumps
        # directly above the threshold.
        # --------------------------------------------------

        if (
            previous_status == "GREEN"
            and current_status == "RED"
        ):

            return Alert(
                camera_id=camera_id,
                zone_id=zone_id,
                zone_name=zone_name,
                previous_status=previous_status,
                current_status=current_status,
                count=count,
                threshold=threshold,
                timestamp=datetime.now(
                    timezone.utc
                ),
                alert_type="THRESHOLD_EXCEEDED",
                active=True,
            )

        # --------------------------------------------------
        # YELLOW → RED
        # --------------------------------------------------

        if (
            previous_status == "YELLOW"
            and current_status == "RED"
        ):

            return Alert(
                camera_id=camera_id,
                zone_id=zone_id,
                zone_name=zone_name,
                previous_status=previous_status,
                current_status=current_status,
                count=count,
                threshold=threshold,
                timestamp=datetime.now(
                    timezone.utc
                ),
                alert_type="THRESHOLD_EXCEEDED",
                active=True,
            )

        # --------------------------------------------------
        # RED → YELLOW
        # --------------------------------------------------

        if (
            previous_status == "RED"
            and current_status == "YELLOW"
        ):

            return Alert(
                camera_id=camera_id,
                zone_id=zone_id,
                zone_name=zone_name,
                previous_status=previous_status,
                current_status=current_status,
                count=count,
                threshold=threshold,
                timestamp=datetime.now(
                    timezone.utc
                ),
                alert_type="THRESHOLD_RECOVERING",
                active=False,
                resolved=True,
            )

        # --------------------------------------------------
        # RED → GREEN
        # --------------------------------------------------

        if (
            previous_status == "RED"
            and current_status == "GREEN"
        ):

            return Alert(
                camera_id=camera_id,
                zone_id=zone_id,
                zone_name=zone_name,
                previous_status=previous_status,
                current_status=current_status,
                count=count,
                threshold=threshold,
                timestamp=datetime.now(
                    timezone.utc
                ),
                alert_type="THRESHOLD_RECOVERED",
                active=False,
                resolved=True,
            )

        # --------------------------------------------------
        # YELLOW → GREEN
        # --------------------------------------------------

        if (
            previous_status == "YELLOW"
            and current_status == "GREEN"
        ):

            return Alert(
                camera_id=camera_id,
                zone_id=zone_id,
                zone_name=zone_name,
                previous_status=previous_status,
                current_status=current_status,
                count=count,
                threshold=threshold,
                timestamp=datetime.now(
                    timezone.utc
                ),
                alert_type="THRESHOLD_RECOVERED",
                active=False,
                resolved=True,
            )

        return None

    # --------------------------------------------------
    # Get current status of a zone
    # --------------------------------------------------

    def get_previous_status(
        self,
        camera_id: str,
        zone_id: str,
    ):

        return self._previous_status.get(
            (
                camera_id,
                zone_id,
            )
        )

    # --------------------------------------------------
    # Reset one zone
    # --------------------------------------------------

    def reset_zone(
        self,
        camera_id: str,
        zone_id: str,
    ):

        self._previous_status.pop(
            (
                camera_id,
                zone_id,
            ),
            None,
        )

    # --------------------------------------------------
    # Reset all zones
    # --------------------------------------------------

    def reset(self):

        self._previous_status.clear()