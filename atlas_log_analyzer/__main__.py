"""Entry point for running atlas-log-analyzer as a module.

Usage:
    python -m atlas_log_analyzer                      # read raw log from stdin
    python -m atlas_log_analyzer --file build.log     # read from file
    python -m atlas_log_analyzer --verbose            # show all patterns, not just summary

Output is JSON:
    {"total_patterns": N, "errors": N, "flaky_signals": N,
     "cache_hits": N, "cache_misses": N, "docker_steps": N,
     "duration_mentions": N, "patterns": [...]}   # patterns only with --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from atlas_log_analyzer.patterns import analyze_log, summarize_hotspots

logging.basicConfig(level=logging.WARNING, format="%(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a CI/CD build log and extract runtime patterns."
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="Path to a log file. Reads from stdin if not specified.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include all matched patterns in the output (not just the summary).",
    )
    args = parser.parse_args()

    if args.file:
        try:
            with open(args.file, encoding="utf-8", errors="replace") as fh:
                raw_log = fh.read()
        except OSError as exc:
            print(f"Error reading file: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        raw_log = sys.stdin.read()

    patterns = analyze_log(raw_log)
    hotspot = summarize_hotspots(patterns)

    output: dict = {
        "total_patterns": hotspot.total_patterns,
        "errors": hotspot.errors,
        "flaky_signals": hotspot.flaky_signals,
        "cache_hits": hotspot.cache_hits,
        "cache_misses": hotspot.cache_misses,
        "docker_steps": hotspot.docker_steps,
        "duration_mentions": hotspot.duration_mentions,
    }

    if args.verbose:
        output["patterns"] = [
            {
                "type": p.pattern_type,
                "severity": p.severity,
                "description": p.description,
                "line": p.line_number,
                "matched_text": p.matched_text,
            }
            for p in patterns
        ]

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
