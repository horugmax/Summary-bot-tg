# src/config.py
import json
import logging
import sys

logger = logging.getLogger(__name__)

def load_config(filename: str) -> dict:
    try:
        with open(filename, "r", encoding="utf-8") as file:
            config = json.load(file)
        logger.info("Config loaded successfully.")
    except FileNotFoundError:
        logger.error(f"Config file '{filename}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in '{filename}': {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"An unexpected error occurred while loading '{filename}': {e}")
        sys.exit(1)

    if not isinstance(config, dict):
        logger.error("Config is not a valid dictionary.")
        sys.exit(1)

    return config
