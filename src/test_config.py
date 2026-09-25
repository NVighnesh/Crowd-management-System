from src.config.settings import load_config


def main():
    config = load_config()
    camera = config["cameras"][0]

    print("System:", config["system"]["name"])
    print("Camera:", camera["id"])
    print("Video:", camera["source"])
    print("Model:", config["inference"]["model"])
    print("Device:", config["inference"]["device"])
    print("Image Size:", config["inference"]["image_size"])
    print("Tracker:", config["tracking"]["tracker"])


if __name__ == "__main__":
    main()