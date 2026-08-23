#!/usr/bin/env python
"""Accuracy proof, not a claim: word error rate against a hand-checked gold
set (jiwer), plus the evidence-verifier's own catch rate — what fraction of
generated citations actually match the transcript at the claimed timestamp.

Usage:
    python scripts/eval_harness.py --gold-dir ../eval/gold_set
"""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-dir", type=Path, required=True,
                         help="directory of hand-checked {call_id}.txt reference transcripts")
    args = parser.parse_args()

    # TODO:
    #  1. for each gold transcript, load the corresponding stored transcript
    #     from SQLite and compute jiwer.wer(reference, hypothesis)
    #  2. for each stored evidence object across all calls, re-run
    #     verifier.verify_evidence and report the overall pass rate
    #  3. print a short report: mean WER, citation pass rate, worst offenders
    raise NotImplementedError


if __name__ == "__main__":
    main()
