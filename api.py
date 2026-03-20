"""FastAPI wrapper around the triage pipeline. Exposes /process, /batch, and /health."""
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from llm_client import LLMClient
from pipeline import process

log = logging.getLogger(__name__)

app = FastAPI(title="ArcVault Triage API", version="1.0.0")

_client: LLMClient | None = None


def get_client() -> LLMClient:
    """Return the shared LLMClient, initialising it on first call."""
    global _client
    if _client is None:
        _client = LLMClient()
        log.info("LLM client initialised: %s / %s", _client.provider, _client.model)
    return _client


class ProcessRequest(BaseModel):
    """Single message triage request."""

    source: str
    message: str


class BatchRequest(BaseModel):
    """Batch of triage requests."""

    requests: list[ProcessRequest]


@app.get("/health")
def health():
    """Return provider info and service status."""
    client = get_client()
    return {"status": "ok", "provider": client.provider, "model": client.model}


@app.post("/process")
def process_single(req: ProcessRequest):
    """Run the full triage pipeline for a single message."""
    if not req.message.strip():
        raise HTTPException(status_code=422, detail="message cannot be empty")
    return process(req.source, req.message, get_client())


@app.post("/batch")
def process_batch(req: BatchRequest):
    """Run the triage pipeline for a list of messages."""
    if not req.requests:
        raise HTTPException(status_code=422, detail="requests list cannot be empty")
    client = get_client()
    return [process(r.source, r.message, client) for r in req.requests]
