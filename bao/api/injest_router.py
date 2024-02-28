from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from bao.api.authenticate import authenticated
from bao.components.crawler.youtube_transcript.transcript_service import (
    TranscriptService,
)
from bao.components.injest.injest_service import InjestService

ingest_router = APIRouter(prefix="/ingest", dependencies=[Depends(authenticated)])


class InjestDocument(BaseModel):
    source: str = Field(
        description="document source. It's the key metadata field in the vector database."
    )
    title: str = Field(description="document title. Youtube title for example.")


class InjestResponse(BaseModel):
    data: list[InjestDocument] = Field(
        description="a list of files/urls that has been injested to vector DB"
    )


@ingest_router.post("/youbute", tags=["Ingestion"])
def ingest_youtube(
    request: Request, youtube_url: str, language: str = "en"
) -> InjestResponse:
    """Ingests from a Youtube URL.
    Note, the short format of youtube url
    """
    crawler: TranscriptService = request.state.injector.get(TranscriptService)
    injestor: InjestService = request.state.injector.get(InjestService)
    entry_file = crawler.extract_from_youtube(video_url=youtube_url, language=language)
    if not entry_file:
        raise HTTPException(
            status_code=401,
            detail="Failed to extract transcripts/subtitles from the video",
        )
    docs = injestor.injest_file(entry_file)
    if not docs:
        return InjestResponse(data=[])
    return InjestResponse(
        data=[InjestDocument(source=youtube_url, title=entry_file.name)]
    )


@ingest_router.post("/yaml", tags=["Ingestion"])
def ingest_yaml(request: Request, yalm_file: UploadFile) -> InjestResponse:
    """Ingests from a yaml file.
    Note, yaml format should be as follow:
    metadata:
       source:
       title:
       pub-date:
       video:
    content: >
       say hi
    """
    injestor: InjestService = request.state.injector.get(InjestService)

    docs = injestor.injest_bin(yalm_file.file)
    if not docs:
        return InjestResponse(data=[])
    metadata = docs[0].metadata
    return InjestResponse(
        data=[InjestDocument(source=metadata.get("source"), title=metadata.get("title"))]  # type: ignore
    )
