from src.crowd.analyzer import CrowdAnalyzer
from src.detection.detection_types import Detection


def create_test_detections():
    return [
        Detection(
            class_id=0,
            confidence=0.95,
            bbox=(100, 100, 150, 200),
        ),
        Detection(
            class_id=0,
            confidence=0.90,
            bbox=(200, 100, 250, 200),
        ),
        Detection(
            class_id=0,
            confidence=0.88,
            bbox=(300, 100, 350, 200),
        ),
    ]


def create_test_zones():
    return [
        {
            "zone_id": "ZONE_001",
            "name": "Test Zone",
            "threshold": 5,
            "threshold_type": "count",
            "polygon": [
                [0, 0],
                [500, 0],
                [500, 500],
                [0, 500],
            ],
        }
    ]


def test_whole_frame_and_zones_enabled():

    analyzer = CrowdAnalyzer(
        whole_frame_enabled=True,
        zones_enabled=True,
        zone_point_mode="bottom_center",
    )

    detections = create_test_detections()
    zones = create_test_zones()

    result = analyzer.analyze(
        camera_id="TEST_CAMERA",
        detections=detections,
        zones=zones,
    )

    if result.total_people != 3:
        raise AssertionError(
            "Whole-frame count should be 3."
        )

    if len(result.zones) != 1:
        raise AssertionError(
            "Zone results should contain 1 zone."
        )

    if result.zones[0].count != 3:
        raise AssertionError(
            "Zone count should be 3."
        )

    print(
        "Whole-frame enabled + "
        "zones enabled: PASS"
    )


def test_whole_frame_disabled():

    analyzer = CrowdAnalyzer(
        whole_frame_enabled=False,
        zones_enabled=True,
        zone_point_mode="bottom_center",
    )

    detections = create_test_detections()
    zones = create_test_zones()

    result = analyzer.analyze(
        camera_id="TEST_CAMERA",
        detections=detections,
        zones=zones,
    )

    if result.total_people is not None:
        raise AssertionError(
            "Whole-frame count should be "
            "disabled and return None."
        )

    if len(result.zones) != 1:
        raise AssertionError(
            "Zone results should still be available."
        )

    print(
        "Whole-frame disabled + "
        "zones enabled: PASS"
    )


def test_zones_disabled():

    analyzer = CrowdAnalyzer(
        whole_frame_enabled=True,
        zones_enabled=False,
        zone_point_mode="bottom_center",
    )

    detections = create_test_detections()
    zones = create_test_zones()

    result = analyzer.analyze(
        camera_id="TEST_CAMERA",
        detections=detections,
        zones=zones,
    )

    if result.total_people != 3:
        raise AssertionError(
            "Whole-frame count should still be 3."
        )

    if len(result.zones) != 0:
        raise AssertionError(
            "Zone results should be empty "
            "when zone counting is disabled."
        )

    print(
        "Whole-frame enabled + "
        "zones disabled: PASS"
    )


def test_both_disabled():

    analyzer = CrowdAnalyzer(
        whole_frame_enabled=False,
        zones_enabled=False,
        zone_point_mode="bottom_center",
    )

    detections = create_test_detections()
    zones = create_test_zones()

    result = analyzer.analyze(
        camera_id="TEST_CAMERA",
        detections=detections,
        zones=zones,
    )

    if result.total_people is not None:
        raise AssertionError(
            "Whole-frame count should be disabled."
        )

    if len(result.zones) != 0:
        raise AssertionError(
            "Zone results should be empty."
        )

    print(
        "Whole-frame disabled + "
        "zones disabled: PASS"
    )


def main():

    print(
        "Testing counting configuration..."
    )

    test_whole_frame_and_zones_enabled()
    test_whole_frame_disabled()
    test_zones_disabled()
    test_both_disabled()

    print(
        "\nCounting configuration test successful."
    )


if __name__ == "__main__":
    main()