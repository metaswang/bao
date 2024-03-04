from pathlib import Path

PROJECT_ROOT_PATH: Path = Path(__file__).parents[1]
MODEL_PATH = PROJECT_ROOT_PATH / "data/models"
MODEL_CACHE = MODEL_PATH / ".cache"
