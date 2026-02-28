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
import os
import sys

from atlas_log_analyzer.patterns import analyze_log, summarize_hotspots
from atlas_sdk.events import LogAnalysisEvent

logging.basicConfig(level=logging.WARNING, format="%(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_stream(redis_url: str) -> None:
    """Consume the atlas.scan.results Redis stream and analyze build logs."""
    import redis as _redis

    logger.info("Connecting to Redis at %s ...", redis_url)
    client = _redis.from_url(redis_url, decode_responses=True)

    stream_in = "atlas.scan.results"
    stream_out = "atlas.logs.analyzed"
    group_name = "atlas-log-analyzer"
    consumer_name = "atlas-log-1"

    try:
        client.xgroup_create(stream_in, group_name, id="0", mkstream=True)
    except _redis.exceptions.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise

    logger.info("Listening on stream '%s' (group=%s)...", stream_in, group_name)
    while True:
        try:
            messages = client.xreadgroup(
                group_name, consumer_name, {stream_in: ">"}, count=1, block=5000
            )
            if not messages:
                continue
            for _stream, entries in messages:
                for msg_id, fields in entries:
                    try:
                        payload = json.loads(fields.get("payload", "{}"))
                        scan_request_id = payload.get("scan_request_id")
                        if not scan_request_id:
                            continue

                        build_logs = payload.get("build_logs", [])
                        if not build_logs:
                            logger.info("Skipping %s: no build logs found.", msg_id)
                            continue

                        # Default to analyzing first log (conceptually)
                        raw_text = build_logs[0].get("content", "")
                        patterns = analyze_log(raw_text)
                        hotspot = summarize_hotspots(patterns)
                        
                        logger.info("Analyzed log for %s, found %d patterns", scan_request_id, len(patterns))

                        event = LogAnalysisEvent(
                            scan_request_id=scan_request_id,
                            total_patterns=hotspot.total_patterns,
                            errors=hotspot.errors,
                            flaky_signals=hotspot.flaky_signals,
                            cache_hits=hotspot.cache_hits,
                            cache_misses=hotspot.cache_misses,
                            docker_steps=hotspot.docker_steps,
                            duration_mentions=hotspot.duration_mentions,
                            patterns=[{
                                "type": p.pattern_type,
                                "description": p.description,
                                "line": p.line_number,
                                "severity": p.severity
                            } for p in patterns]
                        )
                        client.xadd(stream_out, {"payload": event.model_dump_json()})
                    except Exception as exc:  # noqa: BLE001
                        logger.error("Failed to analyze message %s: %s", msg_id, exc)
                    finally:
                        client.xack(stream_in, group_name, msg_id)
        except KeyboardInterrupt:
            logger.info("Shutting down stream consumer.")
            break


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a CI/CD build log and extract runtime patterns."
    )
    parser.add_argument(
        "--mode",
        default=os.environ.get("ATLAS_LOG_MODE", "stdin"),
        choices=["stdin", "stream"],
        help="Operation mode: stdin (default) or stream",
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="Path to a log file. Reads from stdin if not specified (in stdin mode).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include all matched patterns in the output (not just the summary).",
    )
    args = parser.parse_args()
    
    redis_url = os.environ.get("ATLAS_REDIS_URL", "redis://localhost:6379")
    
    if args.mode == "stream":
        run_stream(redis_url)
        return

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
