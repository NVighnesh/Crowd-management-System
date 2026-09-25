from src.alerts.alert import Alert


class AlertSerializer:

    @staticmethod
    def to_dict(alert: Alert) -> dict:

        return {
            "alert_id": alert.alert_id,
            "camera_id": alert.camera_id,
            "zone_id": alert.zone_id,
            "zone_name": alert.zone_name,
            "previous_status": alert.previous_status,
            "current_status": alert.current_status,
            "count": alert.count,
            "threshold": alert.threshold,
            "timestamp": alert.timestamp.isoformat(),
            "alert_type": alert.alert_type,
            "active": alert.active,
            "resolved": alert.resolved,
        }

    @staticmethod
    def to_list(alerts: list[Alert]) -> list[dict]:

        return [
            AlertSerializer.to_dict(alert)
            for alert in alerts
        ]