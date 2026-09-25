import pytest

from src.crowd.whole_frame_counter import (
    WholeFrameCounter,
)
from src.detection.detection_types import Detection


def create_test_detections():

    return [
        Detection(
            class_id=0,
            confidence=0.95,
            bbox=(100, 100, 150, 200),
            track_id=1,
        ),
        Detection(
            class_id=0,
            confidence=0.92,
            bbox=(200, 100, 250, 200),
            track_id=2,
        ),
        Detection(
            class_id=0,
            confidence=0.90,
            bbox=(300, 100, 350, 200),
            track_id=3,
        ),
        Detection(
            class_id=0,
            confidence=0.88,
            bbox=(400, 100, 450, 200),
            track_id=None,
        ),
        Detection(
            class_id=0,
            confidence=0.85,
            bbox=(500, 100, 550, 200),
            track_id=None,
        ),
    ]


@pytest.fixture
def detections():
    return create_test_detections()


def test_detection_mode(detections):

    counter = WholeFrameCounter(
        mode="detection"
    )

    count = counter.count(detections)

    if count != 5:

        raise AssertionError(
            f"Detection mode should return 5, "
            f"but returned {count}."
        )

    print(
        "Detection mode: "
        "5/5 counted: PASS"
    )


def test_tracked_active_mode(detections):

    counter = WholeFrameCounter(
        mode="tracked_active"
    )

    count = counter.count(detections)

    if count != 3:

        raise AssertionError(
            f"Tracked-active mode should return 3, "
            f"but returned {count}."
        )

    print(
        "Tracked-active mode: "
        "3/5 counted: PASS"
    )


def test_invalid_mode(detections):

    try:

        WholeFrameCounter(
            mode="invalid_mode"
        )

    except ValueError:

        print(
            "Invalid mode validation: PASS"
        )

        return

    raise AssertionError(
        "Invalid counting mode should "
        "raise ValueError."
    )


def main():

    print(
        "Testing WholeFrameCounter..."
    )

    detections = create_test_detections()

    test_detection_mode(
        detections
    )

    test_tracked_active_mode(
        detections
    )

    test_invalid_mode(
        detections
    )

    print(
        "\nWholeFrameCounter test successful."
    )


if __name__ == "__main__":
    main()