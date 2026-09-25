import threading

from src.alerts.alert import Alert


class AlertStore:

    def __init__(self, max_alerts=1000):

        if max_alerts <= 0:
            raise ValueError(
                "max_alerts must be greater than zero."
            )

        self.max_alerts = max_alerts

        self._alerts = []

        self._lock = threading.Lock()

    # --------------------------------------------------
    # Add alert
    # --------------------------------------------------

    def add(self, alert: Alert):

        if not isinstance(alert, Alert):
            raise TypeError(
                "AlertStore accepts only Alert objects."
            )

        with self._lock:

            self._alerts.append(alert)

            # Keep only the newest alerts.
            if len(self._alerts) > self.max_alerts:

                excess = (
                    len(self._alerts)
                    - self.max_alerts
                )

                del self._alerts[:excess]

    def load(self, alerts):
        """Restore persisted alerts without changing their order."""
        with self._lock:
            self._alerts = list(alerts)[-self.max_alerts :]

    def resolve_active(self, camera_id: str, zone_id: str):
        with self._lock:
            for alert in self._alerts:
                if (
                    alert.camera_id == camera_id
                    and alert.zone_id == zone_id
                    and alert.active
                ):
                    alert.active = False
                    alert.resolved = True

    # --------------------------------------------------
    # Get all alerts
    # --------------------------------------------------

    def get_all(self):

        with self._lock:

            return list(self._alerts)

    # --------------------------------------------------
    # Get latest alert
    # --------------------------------------------------

    def get_latest(self):

        with self._lock:

            if not self._alerts:
                return None

            return self._alerts[-1]

    # --------------------------------------------------
    # Get alerts for camera
    # --------------------------------------------------

    def get_by_camera(
        self,
        camera_id: str,
    ):

        with self._lock:

            return [
                alert
                for alert in self._alerts
                if alert.camera_id == camera_id
            ]

    # --------------------------------------------------
    # Get alerts for zone
    # --------------------------------------------------

    def get_by_zone(
        self,
        camera_id: str,
        zone_id: str,
    ):

        with self._lock:

            return [
                alert
                for alert in self._alerts
                if (
                    alert.camera_id == camera_id
                    and alert.zone_id == zone_id
                )
            ]

    # --------------------------------------------------
    # Number of stored alerts
    # --------------------------------------------------

    def count(self):

        with self._lock:

            return len(self._alerts)

    # --------------------------------------------------
    # Clear all alerts
    # --------------------------------------------------

    def clear(self):

        with self._lock:

            self._alerts.clear()