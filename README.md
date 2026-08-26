# Call-Centre Radar

Raw stereo call recordings in, a grounded API and admin dashboard out. Every
judgment the system makes — intent, mood shift, resolution, needs-attention
score — carries the timestamp and the words that justify it.

**The design rule: the model is never allowed to write a quote.** It cites a
turn by *number*, under an enforced JSON schema, and the exact words are looked
up from our own transcript. Fabricated citations aren't detected after the fact
— they're structurally impossible to express.

See [RADAR_PLAYBOOK.md](RADAR_PLAYBOOK.md) for the architecture and the
reasoning behind each choice.

---

## Quickstart

**The analysed database ships with this repo.** `data/radar.db` contains all
1,441 calls already transcribed and analysed, so you can skip straight to
serving — no API keys, no cost, no waiting:

```bash
cp .env.example .env
unzip callradar-data.zip -d data/     # audio only; needed for playback
docker compose up backend frontend
```

- Dashboard: **http://localhost:3000**
- API docs: **http://localhost:8000/docs**

`data/cache/` also ships with the raw transcripts, so the analysis layer can be
re-run without paying to transcribe again:

```bash
docker compose run --rm --no-deps backend python scripts/analyze_dataset.py --reanalyze --workers 8
```

---

## Rebuilding from scratch

To regenerate everything from the raw audio, delete `data/radar.db` and
`data/cache/`, then fill in **two** keys in `.env`:

| Variable | For | Getting one |
|---|---|---|
| `ASSEMBLYAI_API_KEY` | transcription | [assemblyai.com](https://www.assemblyai.com) — free credit covers the whole corpus (~$7) |
| `GROQ_API_KEY` | reasoning | [console.groq.com](https://console.groq.com) — free, no card |

```bash
# 1. transcribe — once, cached to data/cache/, never repeated
docker compose run --rm --no-deps backend python scripts/ingest_dataset.py --workers 8

# 2. analyse — mood, reasoning, verified citations, attention, clustering
docker compose run --rm --no-deps backend python scripts/analyze_dataset.py --workers 8

# 3. serve
docker compose up backend frontend
```

Expect roughly **80 minutes** for step 1 and **15 minutes** for step 2.

> **After editing `.env`, run `docker compose up -d --force-recreate backend`.**
> `docker compose restart` does *not* reload environment files, and the symptom
> is a provider error naming credentials you already fixed.

---

## Reasoning providers

Any provider works as long as it enforces a **JSON schema** — that enforcement
is what makes the citation guarantee hold. A provider offering only "valid
JSON" without schema adherence silently breaks the design.

| `LLM_PROVIDER` | Model | Notes |
|---|---|---|
| `groq` | `openai/gpt-oss-20b` | **Default.** Free, fast. Free tier caps at 8k tokens/min and 1k requests/day — fine for `/ingest`, ~3 hours for a full batch |
| `bedrock` | `openai.gpt-oss-120b-1:0` | No rate ceiling. Needs AWS credentials and account verification |
| `azure` | your deployment | Set endpoint, key, deployment name, and a recent `api-version` |
| `ollama` | `qwen3:8b` | Fully offline — see below |

Switching is one line in `.env`. Nothing else changes.

### Fully offline

No API keys, no network, nothing to pay:

```bash
# in .env
TRANSCRIBER_PROVIDER=whisper
LLM_PROVIDER=ollama

docker compose --profile offline up -d ollama
docker compose exec ollama ollama pull qwen3:8b
```

Transcription then takes ~2.5 hours on 12 CPU cores instead of ~80 minutes.

---

## Live ingestion

The **"Analyse a call"** tab (http://localhost:3000/ingest) takes a drag-and-drop
upload, runs the whole pipeline, and opens the finished call with its transcript,
mood timeline and evidence chips already populated.

`POST /ingest` is the same thing from the API — the **same pipeline** the batch
uses (split, transcribe, merge, mood, reasoning, verified citations, attention
score), returning the full analysed call:

```bash
curl -X POST http://localhost:8000/ingest \
  -F "audio=@new-call.mp3" \
  -F "customer_name=Priya Sharma" \
  -F "agent_name=Daniel"
```

Takes ~17s warm. The audio must be **stereo** (left = agent, right =
customer); a mono upload is rejected with an explanation rather than silently
mis-attributed.

> Warm the pipeline with one throwaway ingest before demoing — the first call
> in a fresh container loads the embedding model and takes noticeably longer.

---

## Useful flags

```bash
# time 20 calls before committing to the full run
... ingest_dataset.py --limit 20

# re-run turn merging from CACHED transcripts — no re-transcription, no spend
... ingest_dataset.py --reprocess

# re-run the intelligence layer without touching audio
... analyze_dataset.py --reanalyze

# rebuild issue clusters only
... analyze_dataset.py --cluster-only
```

Transcription and analysis are separate scripts on purpose: transcription is
slow and paid and happens once; analysis is fast and free and gets re-run
constantly while prompts and weights are tuned.

---

## Evaluation

```bash
docker compose run --rm --no-deps backend python scripts/eval_harness.py
```

Reports the **citation pass rate** — what fraction of stored citations actually
occur in the cited turn *and* semantically support the claim — broken down by
claim type, with rejection reasons. Fully automatic, no labelling required.

Measured on the full corpus:

| | |
|---|---|
| Calls analysed | 1,441 |
| Citations | 3,059 |
| **Intent citations verified** | **97.9%** |
| Mood-shift citations verified | 85.9% |
| Resolution citations verified | 81.1% |
| **Overall** | **89.3%** |

"Verified" means the quote provably occurs in the cited turn **and**
semantically supports the claim. The harness re-checks from scratch rather than
trusting the stored flag, so the number can't drift from what the dashboard
shows.

Word error rate also runs if you place hand-checked `{call_id}.txt` transcripts
in `eval/gold_set/` and `pip install -r backend/requirements-ml.txt`.

---

## Project layout

```
backend/    FastAPI service + the transcription/analysis pipeline
frontend/   Next.js (App Router) dashboard
data/       audio/, metadata/, plus generated cache/ and radar.db
eval/       hand-checked gold set for WER
```

The browser never calls FastAPI directly: `next.config.ts` rewrites `/api/*`
and `/audio/*` to the backend, so there's no CORS configuration anywhere and
the audio player's HTTP Range requests stay same-origin.

## Tests

```bash
docker compose run --rm --no-deps backend python -m pytest tests/ -q
```

---

## Known characteristics of this dataset

Worth knowing before reading the dashboard — several shaped the design:

- **1,441 calls, 23.28 hours.** Mean call 58s. All stereo 8 kHz: left channel
  agent, right channel customer, which is why no diarization is needed.
- **Only 4 distinct days** (2020-03-15, 05-30, 06-01, 06-02). "Attention today"
  therefore means *the most recent day that has calls*, not `DATE('now')`. And
  the Trends view ranks by volume and outcome rather than drawing a time series
  over four non-contiguous points — per-day counts there reproduce the
  recording schedule, not any trend.
- **`speaker_id` is not a person.** One customer name maps to 14 different
  speaker_ids. Identity is keyed on name — see `pipeline/metadata.py`.
- **The calls are scripted and polite.** The escalation lexicon fires on
  essentially none of them, so that attention factor rarely contributes and
  scores top out around 55 rather than 90.
- **Mood shifts are reported conservatively.** Change-point detection runs on a
  partly prosodic signal, so it fires on rhythm changes in speech with no
  emotional content — a customer reading out an address. Where the shift turn is
  too short to quote, the system reports *no shift* rather than a claim it
  cannot evidence. That cut shift claims from 451 to 177 and took their
  verification rate from 33% to 86%.
