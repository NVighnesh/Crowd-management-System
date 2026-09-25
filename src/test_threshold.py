from src.crowd.threshold import ThresholdEngine


def main():

    engine = ThresholdEngine()

    test_cases = [
        (3, 5),
        (5, 5),
        (7, 5),
    ]

    for count, threshold in test_cases:

        status = engine.evaluate(
            count,
            threshold
        )

        print(
            f"Count={count}, "
            f"Threshold={threshold}, "
            f"Status={status}"
        )


if __name__ == "__main__":
    main()