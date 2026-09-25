from src.alerts.alert_engine import AlertEngine
from src.alerts.alert_store import AlertStore


class AlertManager:

    def __init__(
        self,
        max_alerts=1000,
    ):

        self.engine = AlertEngine()

        self.store = AlertStore(
            max_alerts=max_alerts
        )

    # --------------------------------------------------
    # Process one crowd analysis result
    # --------------------------------------------------

    def process_result(self, result):

        alerts = []

        for zone in result.zones:

            alert = self.engine.evaluate(
                camera_id=result.camera_id,
                zone_id=zone.zone_id,
                zone_name=zone.name,
                current_status=zone.status,
                count=zone.count,
                threshold=zone.threshold,
            )

            if alert is not None:

                self.store.resolve_active(
                    alert.camera_id,
                    alert.zone_id,
                )

                if alert.current_status == "GREEN":
                    alert.active = False
                    alert.resolved = True

                self.store.add(alert)

                alerts.append(alert)

        return alerts

    def load_alerts(self, alerts):
        self.store.load(alerts)

        for alert in alerts:
            self.engine._previous_status[
                (alert.camera_id, alert.zone_id)
            ] = alert.current_status

    # --------------------------------------------------
    # Get all alerts
    # --------------------------------------------------

    def get_all_alerts(self):

        return self.store.get_all()

    # --------------------------------------------------
    # Get latest alert
    # --------------------------------------------------

    def get_latest_alert(self):

        return self.store.get_latest()

    # --------------------------------------------------
    # Get camera alerts
    # --------------------------------------------------

    def get_camera_alerts(
        self,
        camera_id,
    ):

        return self.store.get_by_camera(
            camera_id
        )

    # --------------------------------------------------
    # Get zone alerts
    # --------------------------------------------------

    def get_zone_alerts(
        self,
        camera_id,
        zone_id,
    ):

        return self.store.get_by_zone(
            camera_id=camera_id,
            zone_id=zone_id,
        )

    # --------------------------------------------------
    # Alert count
    # --------------------------------------------------

    def get_alert_count(self):

        return self.store.count()

    # --------------------------------------------------
    # Reset one zone
    # --------------------------------------------------

    def reset_zone(
        self,
        camera_id,
        zone_id,
    ):

        self.engine.reset_zone(
            camera_id=camera_id,
            zone_id=zone_id,
        )

    # --------------------------------------------------
    # Reset everything
    # --------------------------------------------------

    def reset(self):

        self.engine.reset()

        self.store.clear()