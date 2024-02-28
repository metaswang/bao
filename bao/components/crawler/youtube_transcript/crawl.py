import argparse
import logging
import sys

from bao.components.crawler.youtube_transcript.transcript_service import (
    TranscriptService,
)
from bao.di import global_injector

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# set a root logger
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
parser = argparse.ArgumentParser(description="Crawl transcripts from given video")

parser.add_argument("-v", "--video_url", type=str, help="Youtube video URL")
parser.add_argument(
    "--language",
    type=str,
    default="en",
    help="language that the transcripts should match. e.g. en,cn",
    required=False,
)

args = parser.parse_args()

if __name__ == "__main__":
    transcript_service = global_injector.get(TranscriptService)
    logger.info(f"Crawl output: {transcript_service.settings.crawler.output_dir}")

    transcript_service.extract_from_youtube(
        video_url=args.video_url,
        language=args.language,
    )
