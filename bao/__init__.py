import os
from pathlib import Path
import logging

LOG_LEVEL = "INFO"

PRETTY_LOG_FORMAT = "%(asctime)s.%(msecs)03d [%(levelname)s] %(name)+15s - %(message)s"
logging.basicConfig(
    level=LOG_LEVEL, format=PRETTY_LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"
)
logging.captureWarnings(True)

# disable gradio analytics
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
PROJECT_ROOT_PATH: Path = Path(__file__).parents[1]
MODEL_PATH = PROJECT_ROOT_PATH / "data/models"
MODEL_CACHE = MODEL_PATH / ".cache"
