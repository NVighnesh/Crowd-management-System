from datetime import datetime, timezone

from src.alerts.alert import Alert
from src.alerts.alert_store import AlertStore


def create_alert(
    camera_id,
    zone_id,
    alert_type,
    count,
    threshold,
):
    return Alert(
        camera_id=camera_id,
        zone_id=zone_id,
        zone_name=f"Zone {zone_id}",
        previous_status="GREEN",
        current_status="RED",
        count=count,
        threshold=threshold,
        timestamp=datetime.now(timezone.utc),
        alert_type=alert_type,
    )


def main():

    print("Testing alert store...")

    # --------------------------------------------------
    # Create store
    # --------------------------------------------------

    store = AlertStore(
        max_alerts=3
    )

    print()
    print("Alert store created.")
    print(
        f"  Maximum alerts: "
        f"{store.max_alerts}"
    )

    # --------------------------------------------------
    # Add alerts
    # --------------------------------------------------

    alert_1 = create_alert(
        camera_id="CAM_001",
        zone_id="ZONE_001",
        alert_type="THRESHOLD_EXCEEDED",
        count=15,
        threshold=10,
    )

    alert_2 = create_alert(
        camera_id="CAM_001",
        zone_id="ZONE_002",
        alert_type="THRESHOLD_EXCEEDED",
        count=20,
        threshold=10,
    )

    alert_3 = create_alert(
        camera_id="CAM_002",
        zone_id="ZONE_001",
        alert_type="THRESHOLD_EXCEEDED",
        count=12,
        threshold=10,
    )

    store.add(alert_1)
    store.add(alert_2)
    store.add(alert_3)

    print()
    print(
        f"Alerts stored: "
        f"{store.count()}"
    )

    if store.count() != 3:
        raise AssertionError(
            "Alert count should be 3."
        )

    print("  Add alerts: PASS")

    # --------------------------------------------------
    # Get all alerts
    # --------------------------------------------------

    alerts = store.get_all()

    print()
    print(
        f"All alerts returned: "
        f"{len(alerts)}"
    )

    if len(alerts) != 3:
        raise AssertionError(
            "get_all() returned incorrect count."
        )

    print("  Get all alerts: PASS")

    # --------------------------------------------------
    # Get latest
    # --------------------------------------------------

    latest = store.get_latest()

    print()
    print("Latest alert:")

    if latest is None:
        raise AssertionError(
            "Latest alert should not be None."
        )

    print(
        f"  Camera: "
        f"{latest.camera_id}"
    )

    print(
        f"  Zone: "
        f"{latest.zone_id}"
    )

    print(
        f"  Type: "
        f"{latest.alert_type}"
    )

    if latest is not alert_3:
        raise AssertionError(
            "Latest alert is incorrect."
        )

    print("  Get latest alert: PASS")

    # --------------------------------------------------
    # Get alerts by camera
    # --------------------------------------------------

    camera_1_alerts = (
        store.get_by_camera(
            "CAM_001"
        )
    )

    print()
    print(
        "CAM_001 alerts:"
    )

    for alert in camera_1_alerts:

        print(
            f"  {alert.zone_id}: "
            f"{alert.alert_type}"
        )

    if len(camera_1_alerts) != 2:
        raise AssertionError(
            "CAM_001 should have 2 alerts."
        )

    print(
        "  Camera filtering: PASS"
    )

    # --------------------------------------------------
    # Get alerts by zone
    # --------------------------------------------------

    zone_alerts = (
        store.get_by_zone(
            camera_id="CAM_001",
            zone_id="ZONE_001",
        )
    )

    print()
    print(
        "CAM_001 / ZONE_001 alerts:"
    )

    for alert in zone_alerts:

        print(
            f"  Count: "
            f"{alert.count}"
        )

    if len(zone_alerts) != 1:
        raise AssertionError(
            "ZONE_001 should have 1 alert."
        )

    if zone_alerts[0] is not alert_1:
        raise AssertionError(
            "Incorrect zone alert returned."
        )

    print(
        "  Zone filtering: PASS"
    )

    # --------------------------------------------------
    # Test maximum alert limit
    # --------------------------------------------------

    alert_4 = create_alert(
        camera_id="CAM_003",
        zone_id="ZONE_001",
        alert_type="THRESHOLD_EXCEEDED",
        count=25,
        threshold=10,
    )

    store.add(alert_4)

    print()
    print(
        f"Alerts after adding fourth: "
        f"{store.count()}"
    )

    if store.count() != 3:
        raise AssertionError(
            "AlertStore exceeded max_alerts."
        )

    alerts = store.get_all()

    if alert_1 in alerts:
        raise AssertionError(
            "Oldest alert was not removed."
        )

    if alert_4 not in alerts:
        raise AssertionError(
            "Newest alert was not stored."
        )

    print(
        "  Maximum alert limit: PASS"
    )

    # --------------------------------------------------
    # Clear store
    # --------------------------------------------------

    store.clear()

    print()
    print(
        f"Alerts after clear: "
        f"{store.count()}"
    )

    if store.count() != 0:
        raise AssertionError(
            "AlertStore.clear() failed."
        )

    if store.get_latest() is not None:
        raise AssertionError(
            "Latest alert should be None "
            "after clear."
        )

    print("  Clear store: PASS")

    # --------------------------------------------------
    # Invalid alert type
    # --------------------------------------------------

    print()
    print(
        "Testing invalid object..."
    )

    try:

        store.add("not an alert")

    except TypeError:

        print(
            "  Invalid object handling: PASS"
        )

    else:

        raise AssertionError(
            "AlertStore should reject "
            "non-Alert objects."
        )

    # --------------------------------------------------
    # Invalid max_alerts
    # --------------------------------------------------

    print()
    print(
        "Testing invalid max_alerts..."
    )

    try:

        AlertStore(max_alerts=0)

    except ValueError:

        print(
            "  Invalid max_alerts handling: PASS"
        )

    else:

        raise AssertionError(
            "AlertStore should reject "
            "max_alerts <= 0."
        )

    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

    print()
    print(
        "Alert store test successful."
    )


if __name__ == "__main__":
    main()