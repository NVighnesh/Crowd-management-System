from src.config.settings import load_config
from src.config.validator import ConfigValidator


def main():

    config = load_config()

    ConfigValidator.validate(config)

    print("Configuration validation successful.")


if __name__ == "__main__":
    main()