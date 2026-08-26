"""FastAPI entrypoint. Reads only from storage — the pipeline never runs inline
on a request except via /ingest, which is the explicit live-demo path."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import agents, attention, calls, customers, ingest, trends
from app.config import settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creating the schema on boot means a fresh clone can start the API before
    # the dataset has been ingested — the dashboard renders empty rather than
    # 500ing on a missing table.
    init_db()
    yield


app = FastAPI(
    title="Call-Centre Radar API",
    description="Grounded call-centre intelligence: every judgment cites a timestamp and quote.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(customers.router, prefix="/customers", tags=["customers"])
app.include_router(calls.router, prefix="/calls", tags=["calls"])
app.include_router(attention.router, prefix="/attention", tags=["attention"])
app.include_router(trends.router, prefix="/trends", tags=["trends"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])

# The recordings, served for the dashboard's waveform player. Starlette raises
# at import time if the directory is missing, which would stop the API booting
# on a clone where the dataset hasn't been unzipped yet — so ensure it exists.
_audio_dir = Path(settings.data_dir) / "audio"
_audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(_audio_dir)), name="audio")


@app.get("/health")
def health():
    return {"status": "ok"}
