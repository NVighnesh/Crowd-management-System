from src.alerts.alert_engine import AlertEngine


def main():

    print("Testing alert engine...")

    engine = AlertEngine()

    camera_id = "CAM_001"
    zone_id = "ZONE_001"
    zone_name = "Zone 1"
    threshold = 10

    # --------------------------------------------------
    # 1. First observation
    # --------------------------------------------------

    alert = engine.evaluate(
        camera_id=camera_id,
        zone_id=zone_id,
        zone_name=zone_name,
        current_status="GREEN",
        count=5,
        threshold=threshold,
    )

    print()
    print("First GREEN observation:")
    print(f"  Alert: {alert}")

    if alert is not None:
        raise AssertionError(
            "First observation should not generate an alert."
        )

    print("  First observation: PASS")

    # --------------------------------------------------
    # 2. GREEN → GREEN
    # --------------------------------------------------

    alert = engine.evaluate(
        camera_id=camera_id,
        zone_id=zone_id,
        zone_name=zone_name,
        current_status="GREEN",
        count=7,
        threshold=threshold,
    )

    print()
    print("GREEN → GREEN:")
    print(f"  Alert: {alert}")

    if alert is not None:
        raise AssertionError(
            "GREEN → GREEN should not generate an alert."
        )

    print("  No duplicate alert: PASS")

    # --------------------------------------------------
    # 3. GREEN → YELLOW
    # --------------------------------------------------

    alert = engine.evaluate(
        camera_id=camera_id,
        zone_id=zone_id,
        zone_name=zone_name,
        current_status="YELLOW",
        count=10,
        threshold=threshold,
    )

    print()
    print("GREEN → YELLOW:")
    print(f"  Alert type: {alert.alert_type}")

    if alert is None:
        raise AssertionError(
            "GREEN → YELLOW should generate an alert."
        )

    if alert.alert_type != "THRESHOLD_REACHED":
        raise AssertionError(
            "Incorrect alert type for GREEN → YELLOW."
        )

    print("  Threshold reached alert: PASS")

    # --------------------------------------------------
    # 4. YELLOW → YELLOW
    # --------------------------------------------------

    alert = engine.evaluate(
        camera_id=camera_id,
        zone_id=zone_id,
        zone_name=zone_name,
        current_status="YELLOW",
        count=10,
        threshold=threshold,
    )

    print()
    print("YELLOW → YELLOW:")
    print(f"  Alert: {alert}")

    if alert is not None:
        raise AssertionError(
            "YELLOW → YELLOW should not generate an alert."
        )

    print("  No duplicate alert: PASS")

    # --------------------------------------------------
    # 5. YELLOW → RED
    # --------------------------------------------------

    alert = engine.evaluate(
        camera_id=camera_id,
        zone_id=zone_id,
        zone_name=zone_name,
        current_status="RED",
        count=15,
        threshold=threshold,
    )

    print()
    print("YELLOW → RED:")
    print(f"  Alert type: {alert.alert_type}")

    if alert is None:
        raise AssertionError(
            "YELLOW → RED should generate an alert."
        )

    if alert.alert_type != "THRESHOLD_EXCEEDED":
        raise AssertionError(
            "Incorrect alert type for YELLOW → RED."
        )

    if alert.count != 15:
        raise AssertionError(
            "Alert count is incorrect."
        )

    if alert.threshold != 10:
        raise AssertionError(
            "Alert threshold is incorrect."
        )

    print("  Threshold exceeded alert: PASS")

    # --------------------------------------------------
    # 6. RED → RED
    # --------------------------------------------------

    alert = engine.evaluate(
        camera_id=camera_id,
        zone_id=zone_id,
        zone_name=zone_name,
        current_status="RED",
        count=18,
        threshold=threshold,
    )

    print()
    print("RED → RED:")
    print(f"  Alert: {alert}")

    if alert is not None:
        raise AssertionError(
            "RED → RED should not generate duplicate alerts."
        )

    print("  Duplicate prevention: PASS")

    # --------------------------------------------------
    # 7. RED → YELLOW
    # --------------------------------------------------

    alert = engine.evaluate(
        camera_id=camera_id,
        zone_id=zone_id,
        zone_name=zone_name,
        current_status="YELLOW",
        count=10,
        threshold=threshold,
    )

    print()
    print("RED → YELLOW:")
    print(f"  Alert type: {alert.alert_type}")

    if alert is None:
        raise AssertionError(
            "RED → YELLOW should generate an alert."
        )

    if alert.alert_type != "THRESHOLD_RECOVERING":
        raise AssertionError(
            "Incorrect alert type for RED → YELLOW."
        )

    print("  Recovery transition: PASS")

    # --------------------------------------------------
    # 8. YELLOW → GREEN
    # --------------------------------------------------

    alert = engine.evaluate(
        camera_id=camera_id,
        zone_id=zone_id,
        zone_name=zone_name,
        current_status="GREEN",
        count=5,
        threshold=threshold,
    )

    print()
    print("YELLOW → GREEN:")
    print(f"  Alert type: {alert.alert_type}")

    if alert is None:
        raise AssertionError(
            "YELLOW → GREEN should generate an alert."
        )

    if alert.alert_type != "THRESHOLD_RECOVERED":
        raise AssertionError(
            "Incorrect alert type for YELLOW → GREEN."
        )

    print("  Recovery completed: PASS")

    # --------------------------------------------------
    # 9. Verify stored status
    # --------------------------------------------------

    status = engine.get_previous_status(
        camera_id=camera_id,
        zone_id=zone_id,
    )

    print()
    print(
        "Current stored zone status:"
    )
    print(f"  {status}")

    if status != "GREEN":
        raise AssertionError(
            "Alert engine stored incorrect zone status."
        )

    print("  Status tracking: PASS")

    # --------------------------------------------------
    # 10. Test independent zones
    # --------------------------------------------------

    alert = engine.evaluate(
        camera_id="CAM_001",
        zone_id="ZONE_002",
        zone_name="Zone 2",
        current_status="RED",
        count=20,
        threshold=10,
    )

    print()
    print(
        "Independent zone first RED observation:"
    )
    print(f"  Alert: {alert}")

    if alert is not None:
        raise AssertionError(
            "First observation of another zone "
            "should not generate an alert."
        )

    status_zone_1 = engine.get_previous_status(
        "CAM_001",
        "ZONE_001",
    )

    status_zone_2 = engine.get_previous_status(
        "CAM_001",
        "ZONE_002",
    )

    if status_zone_1 != "GREEN":
        raise AssertionError(
            "ZONE_001 status was incorrectly affected."
        )

    if status_zone_2 != "RED":
        raise AssertionError(
            "ZONE_002 status was not stored correctly."
        )

    print(
        "  Independent zone tracking: PASS"
    )

    # --------------------------------------------------
    # 11. Reset one zone
    # --------------------------------------------------

    engine.reset_zone(
        camera_id="CAM_001",
        zone_id="ZONE_002",
    )

    status = engine.get_previous_status(
        "CAM_001",
        "ZONE_002",
    )

    print()
    print("Reset ZONE_002:")
    print(f"  Status: {status}")

    if status is not None:
        raise AssertionError(
            "Zone reset failed."
        )

    print("  Zone reset: PASS")

    # --------------------------------------------------
    # 12. Reset entire engine
    # --------------------------------------------------

    engine.reset()

    status = engine.get_previous_status(
        "CAM_001",
        "ZONE_001",
    )

    print()
    print("Reset entire alert engine:")
    print(f"  ZONE_001 status: {status}")

    if status is not None:
        raise AssertionError(
            "Full alert engine reset failed."
        )

    print("  Full reset: PASS")

    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

    print()
    print(
        "Alert engine test successful."
    )


if __name__ == "__main__":
    main()