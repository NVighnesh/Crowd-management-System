import time

from src.crowd.result import CrowdAnalysisResult
from src.crowd.result_store import ResultStore


def main():

    store = ResultStore()

    # --------------------------------------------------
    # Create a sample crowd result
    # --------------------------------------------------

    result = CrowdAnalysisResult(
        camera_id="CAM_TEST",
        total_people=10,
        zones=[],
    )

    # --------------------------------------------------
    # Store result
    # --------------------------------------------------

    store.update(
        camera_id="CAM_TEST",
        result=result,
    )

    # --------------------------------------------------
    # Retrieve stored result
    # --------------------------------------------------

    entry = store.get_with_timestamp(
        "CAM_TEST"
    )

    if entry is None:

        raise RuntimeError(
            "Result was not stored."
        )

    result_timestamp = entry[
        "timestamp"
    ]

    # --------------------------------------------------
    # Test immediately after storing
    # --------------------------------------------------

    age_seconds = (
        time.time()
        - result_timestamp
    )

    max_result_age = 5

    fresh = (
        age_seconds
        <= max_result_age
    )

    print(
        f"Immediate result age: "
        f"{age_seconds:.4f} seconds"
    )

    print(
        f"Immediate freshness: "
        f"{fresh}"
    )

    if not fresh:

        raise AssertionError(
            "A newly stored result "
            "should be fresh."
        )

    # --------------------------------------------------
    # Simulate an old result
    # --------------------------------------------------

    old_timestamp = (
        time.time()
        - 10
    )

    with store._lock:

        store._results[
            "CAM_TEST"
        ]["timestamp"] = old_timestamp

    # --------------------------------------------------
    # Test old result
    # --------------------------------------------------

    entry = store.get_with_timestamp(
        "CAM_TEST"
    )

    result_timestamp = entry[
        "timestamp"
    ]

    age_seconds = (
        time.time()
        - result_timestamp
    )

    fresh = (
        age_seconds
        <= max_result_age
    )

    print(
        f"Old result age: "
        f"{age_seconds:.2f} seconds"
    )

    print(
        f"Old result freshness: "
        f"{fresh}"
    )

    if fresh:

        raise AssertionError(
            "An old result should "
            "not be fresh."
        )

    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

    print(
        "\nResult freshness test successful."
    )


if __name__ == "__main__":
    main()