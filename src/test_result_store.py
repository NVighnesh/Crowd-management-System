from src.crowd.result_store import ResultStore


def main():

    store = ResultStore()

    store.update(
        "CAM_001",
        {
            "total_people": 25,
            "status": "GREEN",
        },
    )

    store.update(
        "CAM_002",
        {
            "total_people": 60,
            "status": "RED",
        },
    )

    print("CAM_001:")
    print(store.get("CAM_001"))

    print("\nCAM_002:")
    print(store.get("CAM_002"))

    print("\nAll results:")
    print(store.get_all())

    store.remove("CAM_001")

    print("\nAfter removing CAM_001:")
    print(store.get_all())

    store.clear()

    print("\nAfter clearing:")
    print(store.get_all())

    print("\nResultStore test complete.")


if __name__ == "__main__":
    main()