import argparse
import logging
import sys

from bao.components.injest.injest_service import InjestService
from bao.di import global_injector

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add a console handler
handler = logging.StreamHandler(sys.stdout)

# Set the formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)

parser = argparse.ArgumentParser(
    description="Call Injest service to add or remove documents from vector db!"
)

parser.add_argument("--injest", action="store_true", help="Data injest", required=False)
parser.add_argument(
    "--remove", action="store_true", help="Data deletion", required=False
)
parser.add_argument(
    "--filter-key", type=str, help="Filter by key", default="source", required=False
)
parser.add_argument(
    "--filter-value",
    type=str,
    help="Filter values, comma as seperator",
    required=False,
)

args = parser.parse_args()
if __name__ == "__main__":
    injest_service = global_injector.get(InjestService)
    if args.injest:
        injest_service.injest_folder()
    elif args.remove:
        meta_key = args.filter_key
        meta_values = args.filter_value.split(",")
        injest_service.remove(source_key=meta_key, source_values=meta_values)
