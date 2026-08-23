# Call-Centre Radar

A call-centre analysis system: raw stereo recordings in, a grounded API and admin
dashboard out. Every judgment the system makes — intent, mood shift, resolution,
needs-attention score — carries the timestamp and quote that justifies it.

See [RADAR_PLAYBOOK.md](RADAR_PLAYBOOK.md) for the full architecture and build plan.

## Quickstart

```bash
cp .env.example .env
# fill in ASSEMBLYAI_API_KEY, or set TRANSCRIBER_PROVIDER=whisper to run fully offline

# 1. unzip the dataset into data/
unzip callradar-data.zip -d data/

# 2. bring up the local LLM, backend, and frontend
docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5:14b-instruct
docker compose up --build

# 3. run the pipeline over the dataset (transcribe -> analyze -> store)
docker compose exec backend python scripts/ingest_dataset.py --data-dir /app/data
```

- API: http://localhost:8000/docs
- Dashboard: http://localhost:5173

## Project layout

```
backend/    FastAPI service + the transcription/analysis pipeline
frontend/   React dashboard
data/       callradar-data.zip contents (audio/, metadata/) + the generated SQLite DB
eval/       hand-checked gold set for WER + evidence-verification accuracy
```

## Configuration

All runtime configuration is via `.env` — see `.env.example`. The transcription
backend is swappable without code changes: `TRANSCRIBER_PROVIDER=assemblyai`
(primary) or `whisper` (offline fallback, no API key required).

## Evaluation

```bash
python backend/scripts/eval_harness.py --gold-dir eval/gold_set
```

Reports word error rate against the hand-checked transcripts and the
evidence-verifier's pass rate (how many generated citations actually match the
transcript at the claimed timestamp).

## Known limitations

_TODO — fill in as the build progresses._
