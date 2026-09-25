from src.alerts.alert_manager import AlertManager
from src.crowd.result import CrowdAnalysisResult, ZoneResult


def create_result(
    camera_id,
    zone_status,
    zone_count,
    threshold=10,
):

    return CrowdAnalysisResult(
        camera_id=camera_id,
        total_people=zone_count,
        zones=[
            ZoneResult(
                zone_id="ZONE_001",
                name="Zone 1",
                count=zone_count,
                threshold=threshold,
                status=zone_status,
            )
        ],
    )


def main():

    print("Testing alert manager...")

    manager = AlertManager(
        max_alerts=10
    )

    # --------------------------------------------------
    # 1. First observation
    # --------------------------------------------------

    result = create_result(
        camera_id="CAM_001",
        zone_status="GREEN",
        zone_count=5,
    )

    alerts = manager.process_result(result)

    print()
    print("First GREEN result:")
    print(f"  Alerts generated: {len(alerts)}")

    if len(alerts) != 0:
        raise AssertionError(
            "First observation should not generate an alert."
        )

    if manager.get_alert_count() != 0:
        raise AssertionError(
            "Alert store should be empty."
        )

    print("  First observation: PASS")

    # --------------------------------------------------
    # 2. GREEN → YELLOW
    # --------------------------------------------------

    result = create_result(
        camera_id="CAM_001",
        zone_status="YELLOW",
        zone_count=10,
    )

    alerts = manager.process_result(result)

    print()
    print("GREEN → YELLOW:")
    print(f"  Alerts generated: {len(alerts)}")

    if len(alerts) != 1:
        raise AssertionError(
            "GREEN → YELLOW should generate one alert."
        )

    if alerts[0].alert_type != "THRESHOLD_REACHED":
        raise AssertionError(
            "Incorrect alert type."
        )

    if manager.get_alert_count() != 1:
        raise AssertionError(
            "Alert store should contain one alert."
        )

    print("  Threshold reached: PASS")

    # --------------------------------------------------
    # 3. YELLOW → YELLOW
    # --------------------------------------------------

    result = create_result(
        camera_id="CAM_001",
        zone_status="YELLOW",
        zone_count=10,
    )

    alerts = manager.process_result(result)

    print()
    print("YELLOW → YELLOW:")
    print(f"  Alerts generated: {len(alerts)}")

    if len(alerts) != 0:
        raise AssertionError(
            "YELLOW → YELLOW should not generate an alert."
        )

    if manager.get_alert_count() != 1:
        raise AssertionError(
            "Duplicate alert was stored."
        )

    print("  Duplicate prevention: PASS")

    # --------------------------------------------------
    # 4. YELLOW → RED
    # --------------------------------------------------

    result = create_result(
        camera_id="CAM_001",
        zone_status="RED",
        zone_count=15,
    )

    alerts = manager.process_result(result)

    print()
    print("YELLOW → RED:")
    print(f"  Alerts generated: {len(alerts)}")

    if len(alerts) != 1:
        raise AssertionError(
            "YELLOW → RED should generate one alert."
        )

    if alerts[0].alert_type != "THRESHOLD_EXCEEDED":
        raise AssertionError(
            "Incorrect RED alert type."
        )

    if alerts[0].count != 15:
        raise AssertionError(
            "Incorrect alert count."
        )

    if manager.get_alert_count() != 2:
        raise AssertionError(
            "Alert store should contain two alerts."
        )

    print("  Threshold exceeded: PASS")

    # --------------------------------------------------
    # 5. RED → RED
    # --------------------------------------------------

    result = create_result(
        camera_id="CAM_001",
        zone_status="RED",
        zone_count=18,
    )

    alerts = manager.process_result(result)

    print()
    print("RED → RED:")
    print(f"  Alerts generated: {len(alerts)}")

    if len(alerts) != 0:
        raise AssertionError(
            "RED → RED should not generate duplicate alerts."
        )

    if manager.get_alert_count() != 2:
        raise AssertionError(
            "Duplicate RED alert was stored."
        )

    print("  Duplicate prevention: PASS")

    # --------------------------------------------------
    # 6. RED → GREEN
    # --------------------------------------------------

    result = create_result(
        camera_id="CAM_001",
        zone_status="GREEN",
        zone_count=5,
    )

    alerts = manager.process_result(result)

    print()
    print("RED → GREEN:")
    print(f"  Alerts generated: {len(alerts)}")

    if len(alerts) != 1:
        raise AssertionError(
            "RED → GREEN should generate one alert."
        )

    if alerts[0].alert_type != "THRESHOLD_RECOVERED":
        raise AssertionError(
            "Incorrect recovery alert type."
        )

    if manager.get_alert_count() != 3:
        raise AssertionError(
            "Recovery alert was not stored."
        )

    print("  Recovery alert: PASS")

    # --------------------------------------------------
    # 7. Independent camera
    # --------------------------------------------------

    result = create_result(
        camera_id="CAM_002",
        zone_status="RED",
        zone_count=20,
    )

    alerts = manager.process_result(result)

    print()
    print(
        "CAM_002 first RED observation:"
    )
    print(
        f"  Alerts generated: "
        f"{len(alerts)}"
    )

    if len(alerts) != 0:
        raise AssertionError(
            "First observation for another camera "
            "should not generate an alert."
        )

    print(
        "  Independent camera state: PASS"
    )

    # --------------------------------------------------
    # 8. Camera filtering
    # --------------------------------------------------

    camera_1_alerts = (
        manager.get_camera_alerts(
            "CAM_001"
        )
    )

    camera_2_alerts = (
        manager.get_camera_alerts(
            "CAM_002"
        )
    )

    print()
    print(
        f"CAM_001 stored alerts: "
        f"{len(camera_1_alerts)}"
    )

    print(
        f"CAM_002 stored alerts: "
        f"{len(camera_2_alerts)}"
    )

    if len(camera_1_alerts) != 3:
        raise AssertionError(
            "CAM_001 should have three alerts."
        )

    if len(camera_2_alerts) != 0:
        raise AssertionError(
            "CAM_002 should have no alerts yet."
        )

    print(
        "  Camera alert filtering: PASS"
    )

    # --------------------------------------------------
    # 9. Latest alert
    # --------------------------------------------------

    latest = manager.get_latest_alert()

    print()
    print("Latest alert:")

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

    if latest.camera_id != "CAM_001":
        raise AssertionError(
            "Incorrect latest alert camera."
        )

    if latest.alert_type != "THRESHOLD_RECOVERED":
        raise AssertionError(
            "Incorrect latest alert type."
        )

    print(
        "  Latest alert retrieval: PASS"
    )

    # --------------------------------------------------
    # 10. Reset
    # --------------------------------------------------

    manager.reset()

    if manager.get_alert_count() != 0:
        raise AssertionError(
            "Alert manager reset did not clear alerts."
        )

    if manager.engine.get_previous_status(
        "CAM_001",
        "ZONE_001",
    ) is not None:

        raise AssertionError(
            "Alert manager reset did not clear engine state."
        )

    print()
    print("Alert manager reset: PASS")

    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

    print()
    print(
        "Alert manager test successful."
    )


if __name__ == "__main__":
    main()