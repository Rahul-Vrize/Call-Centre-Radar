#!/usr/bin/env python
"""Run the full pipeline over every call in the dataset once, caching results
in SQLite. "Do not re-transcribe on every request" — this script is the only
place bulk transcription happens; the API and dashboard only ever read the
result. Re-running is safe: already-processed call ids are skipped.

Usage:
    python scripts/ingest_dataset.py --data-dir ./data
"""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True,
                         help="directory containing audio/ and metadata/ from callradar-data.zip")
    parser.add_argument("--limit", type=int, default=None,
                         help="process only the first N calls (for the day-1 throughput test)")
    args = parser.parse_args()

    # TODO:
    #  1. init_db()
    #  2. for each metadata/<id>.json (respecting --limit):
    #       - upsert customer/agent rows
    #       - skip if calls.id already has processed_at set
    #       - run_batch.process_call(id, audio/<id>.mp3, work_dir)
    #  3. after the full batch: clustering.embed_summaries + cluster_calls
    #     over all calls, to populate issue_clusters / call_clusters
    raise NotImplementedError


if __name__ == "__main__":
    main()
