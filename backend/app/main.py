"""FastAPI entrypoint. Reads only from storage — the pipeline never runs inline
on a request except via /ingest, which is the explicit live-demo path."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api import customers, calls, attention, trends, agents, ingest

app = FastAPI(
    title="Call-Centre Radar API",
    description="Grounded call-centre intelligence: every judgment cites a timestamp and quote.",
    version="0.1.0",
)

app.include_router(customers.router, prefix="/customers", tags=["customers"])
app.include_router(calls.router, prefix="/calls", tags=["calls"])
app.include_router(attention.router, prefix="/attention", tags=["attention"])
app.include_router(trends.router, prefix="/trends", tags=["trends"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])

app.mount("/audio", StaticFiles(directory=f"{settings.data_dir}/audio"), name="audio")


@app.get("/health")
def health():
    return {"status": "ok"}
