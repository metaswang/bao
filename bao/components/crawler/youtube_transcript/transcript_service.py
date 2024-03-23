"""Extract the subtitle given youtube URL"""

import io
import logging
from pathlib import Path
from typing import Any, Dict, List
from injector import singleton, inject

import requests
from bs4 import BeautifulSoup
from bao.settings.settings import Settings

from bao.utils.strings import format_seconds, seconds_to_hh_mm_ss

import yaml

logger = logging.getLogger(__name__)


@singleton
class TranscriptService:

    @inject
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_title_pubdate(self, video_url: str) -> tuple:
        r = requests.get(video_url)
        soup = BeautifulSoup(r.text, features="lxml")
        link = soup.find_all(name="title")[0]
        title = link.text.strip()
        pub_date = soup.find_all(name="meta")[-3]["content"][:10]
        return title, pub_date.replace("-", "")

    def get_transcripts(self, video_url: str, language: str = "en"):
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except:
            logger.exception(
                "cannot import youtube_transcript_api. try 'pip install -U youtube_transcript_api' "
            )
        video_id = (
            video_url.split("v=")[-1].split("&")[0]
            if not video_url.startswith(self.settings.crawler.youtube_short_url_domain)
            else video_url.split("/")[-1].split("?")[0]  # when short url
        )
        try:
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, languages=(language,)
            )
            for d in transcript:
                d["end"] = d["start"] + d["duration"]
                del d["duration"]
            return transcript
        except Exception as e:
            logging.exception(
                f"Failed to retreive transcripts from video: {video_url}", e
            )

    def extract_from_youtube(
        self,
        video_url: str,
        language: str = "en",
    ) -> Path:  # type: ignore
        """
        Extracts transcript from a Youtube video.

        Args:
            video_url: URL of the Youtube video.

        Returns:
            list: List of transcript segments with start time, end time, and text.
        """

        # Download video audio (optional)
        # You can comment out this section if you already have the audio file.
        try:
            import pytube
        except:
            logger.exception(
                "import pytube failed. you need to 'pip install -U pytube'"
            )
        try:
            import whisper
        except:
            logger.exception(
                "import pytube failed. you need to 'pip install -U openai-whisper'"
            )
        title, pub_date = self.get_title_pubdate(video_url)
        try:
            audio_fname = title
            # try to call api to get the transcription
            segments = self.get_transcripts(video_url=video_url, language=language)
            output_dir = Path(self.settings.crawler.output_dir)
            if not segments:
                # Download the audio and extract the transcripts via openai.whisper model
                yt = pytube.YouTube(video_url)
                stream = yt.streams.filter(only_audio=True).first()
                if stream is not None:
                    stream.download(
                        output_path=str(output_dir), filename=f"{audio_fname}.mp4"
                    )
                else:
                    raise ValueError(f"cannot extract audio from {video_url}")
                model = whisper.load_model(self.settings.crawler.whisper_model)
                result = model.transcribe(
                    str(output_dir / f"{audio_fname}.mp4"), language=language
                )
                segments = [
                    {"start": _["start"], "end": _["end"], "text": _["text"]}  # type: ignore
                    for _ in result["segments"]
                ]
            self.persist(
                video_url,
                video_url,
                title,
                pub_date,
                segments,
                output_dir,
                audio_fname,
                self.settings.crawler.transcript_merge_size,
            )
            return output_dir / f"{audio_fname}.yaml"
        except Exception as e:
            logger.exception(
                f"failed to extract transcripts from video: {video_url}", e
            )

    def extract_from_srt_file(
        self, srt_file: str, source, video, title, pub_date
    ) -> Path:
        """
        Transcript as srt format:
        ```
        1
        00:30:40,325 --> 00:30:43,325
        各位战友 观众 听众朋友们大家好
        ```
        Return the yaml file path which contains the transcript metadata and content as below format:
        metadata:
             source:
            video:
            title:
            pub-date:
        content: >
            hi every one!
        """
        srt_f = Path(srt_file)
        if not srt_f.exists() or not srt_f.is_file():
            raise ValueError(f"File path:{srt_f} is invalid.")

        segments = []
        with open(srt_f, "r", encoding="utf-8") as f:
            content = f.read()
        blocks = content.split("\n\n")

        for block in blocks:
            lines = block.splitlines()
            if lines:
                start, end = lines[1].split(" --> ")
                start_time = (
                    int(start[:2]),
                    int(start[3:5]),
                    int(start[6:8]),
                    int(start[9:12]),
                )
                end_time = int(end[:2]), int(end[3:5]), int(end[6:8]), int(end[9:12])
                content = "\n".join(lines[2:])
                segments.append(
                    {
                        "start": start_time[0] * 3600
                        + start_time[1] * 60
                        + start_time[2]
                        + start_time[3] / 1000,
                        "end": end_time[0] * 3600
                        + end_time[1] * 60
                        + end_time[2]
                        + end_time[3] / 1000,
                        "text": content.strip(),
                    }
                )

        output_path = Path(self.settings.crawler.output_dir)
        self.persist(
            video,
            source,
            title,
            pub_date,
            segments,
            output_path,
            title,
            self.settings.crawler.transcript_merge_size,
        )
        return output_path / f"{title}.yaml"

    def persist(
        self,
        video_url: str,
        source: str,
        title: str,
        pub_date: str,
        segments: List[Dict[str, Any]],
        output_dir: Path,
        audio_fname: str,
        chunk_size: int,
    ):
        # write the transcripts into vtt file format
        with open(output_dir / f"{audio_fname}.vtt", "w") as f:
            f.write("WEBVTT\n\n")
            for s in segments:
                f.write(
                    f"{format_seconds(s['start'])} --> {format_seconds(s['end'])}\n"
                )
                f.write(f"""{s["text"]}\n\n""")
        # write meta and content data into yaml file
        with open(output_dir / f"{audio_fname}.yaml", "w", encoding="utf-8") as f:
            io_content = io.StringIO()
            txt_len = 0
            for i, s in enumerate(segments):
                seconds = int(s["start"])
                txt_len += len(s["text"])
                if i == 0:
                    io_content.write(f"{seconds_to_hh_mm_ss(seconds=seconds)} ")
                if txt_len < chunk_size:
                    io_content.write(f"{s['text']} ")
                else:
                    io_content.write(f"\n{seconds_to_hh_mm_ss(seconds)} {s['text']}")
                    txt_len = 0

            yaml.dump(
                {
                    "metadata": {
                        "pub-date": pub_date,
                        "title": title,
                        "video": video_url,
                        "source": source,
                    },
                    "content": io_content.getvalue().strip(),
                },
                f,
            )
