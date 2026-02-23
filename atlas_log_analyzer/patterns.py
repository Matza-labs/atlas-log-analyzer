"""Log pattern extraction — deterministic regex-based analysis.

Extracts runtime behavior from CI/CD build logs using pattern matching:
- Performance hotspots (step durations)
- Flaky test patterns (intermittent failures)
- Error categories (network, permission, OOM, timeout)
- Docker build layers and cache hits
- Retry patterns
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LogPattern:
    """A detected pattern in a build log."""

    pattern_type: str
    description: str
    line_number: int | None = None
    matched_text: str = ""
    severity: str = "info"
    metadata: dict[str, Any] = field(default_factory=dict)


# --- Compiled regex patterns ---

ERROR_PATTERNS = [
    (re.compile(r"(?i)(?:error|fatal|exception|traceback|failed)", re.MULTILINE), "error", "Error or exception detected"),
    (re.compile(r"(?i)out of memory|oom|cannot allocate", re.MULTILINE), "oom", "Out of memory condition"),
    (re.compile(r"(?i)connection refused|timeout|timed out|ETIMEDOUT|ECONNREFUSED", re.MULTILINE), "network", "Network connectivity issue"),
    (re.compile(r"(?i)permission denied|access denied|unauthorized|403 Forbidden", re.MULTILINE), "permission", "Permission or access error"),
    (re.compile(r"(?i)disk full|no space left on device", re.MULTILINE), "disk", "Disk space exhaustion"),
]

FLAKY_PATTERNS = [
    (re.compile(r"(?i)retry|retrying|attempt \d+ of \d+", re.MULTILINE), "retry", "Retry attempt detected"),
    (re.compile(r"(?i)flaky|intermittent|unstable", re.MULTILINE), "flaky", "Flaky test or instability marker"),
    (re.compile(r"(?i)test.*(?:passed|failed).*(?:passed|failed)", re.MULTILINE), "flip", "Test result flipped"),
]

PERFORMANCE_PATTERNS = [
    (re.compile(r"(?:took|completed in|duration:?|elapsed:?)\s*(\d+(?:\.\d+)?)\s*(?:s|sec|seconds|ms|minutes?|min)", re.IGNORECASE), "duration", "Step duration detected"),
    (re.compile(r"(?i)cache (?:hit|restored|found)", re.MULTILINE), "cache_hit", "Cache hit — good for performance"),
    (re.compile(r"(?i)cache (?:miss|not found|empty)", re.MULTILINE), "cache_miss", "Cache miss — opportunity to improve"),
    (re.compile(r"(?i)downloading|pulling|fetching.*(?:\d+(?:\.\d+)?\s*(?:MB|GB|KB))", re.MULTILINE), "download", "Large download detected"),
]

DOCKER_PATTERNS = [
    (re.compile(r"Step\s+(\d+)/(\d+)\s*:", re.MULTILINE), "docker_step", "Docker build step"),
    (re.compile(r"(?i)using cache|---> Using cache", re.MULTILINE), "docker_cache", "Docker layer cache hit"),
    (re.compile(r"(?i)Successfully built\s+([a-f0-9]+)", re.MULTILINE), "docker_built", "Docker image built successfully"),
]


def analyze_log(raw_log: str) -> list[LogPattern]:
    """Analyze a raw build log and extract all detected patterns.

    Args:
        raw_log: The full build log text.

    Returns:
        List of detected LogPattern instances, ordered by line number.
    """
    patterns: list[LogPattern] = []
    lines = raw_log.split("\n")

    for line_num, line in enumerate(lines, 1):
        # Error patterns
        for regex, pattern_type, desc in ERROR_PATTERNS:
            if regex.search(line):
                patterns.append(LogPattern(
                    pattern_type=f"error:{pattern_type}",
                    description=desc,
                    line_number=line_num,
                    matched_text=line.strip()[:200],
                    severity="high" if pattern_type in ("oom", "disk") else "medium",
                ))

        # Flaky patterns
        for regex, pattern_type, desc in FLAKY_PATTERNS:
            if regex.search(line):
                patterns.append(LogPattern(
                    pattern_type=f"flaky:{pattern_type}",
                    description=desc,
                    line_number=line_num,
                    matched_text=line.strip()[:200],
                    severity="medium",
                ))

        # Performance patterns
        for regex, pattern_type, desc in PERFORMANCE_PATTERNS:
            match = regex.search(line)
            if match:
                meta: dict[str, Any] = {}
                if pattern_type == "duration" and match.groups():
                    meta["value"] = match.group(1)
                patterns.append(LogPattern(
                    pattern_type=f"perf:{pattern_type}",
                    description=desc,
                    line_number=line_num,
                    matched_text=line.strip()[:200],
                    severity="info",
                    metadata=meta,
                ))

        # Docker patterns
        for regex, pattern_type, desc in DOCKER_PATTERNS:
            if regex.search(line):
                patterns.append(LogPattern(
                    pattern_type=f"docker:{pattern_type}",
                    description=desc,
                    line_number=line_num,
                    matched_text=line.strip()[:200],
                    severity="info",
                ))

    logger.info("Analyzed %d lines, found %d patterns.", len(lines), len(patterns))
    return patterns


@dataclass
class HotspotReport:
    """Summary of performance hotspots in the log."""

    total_patterns: int = 0
    errors: int = 0
    flaky_signals: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    docker_steps: int = 0
    duration_mentions: int = 0


def summarize_hotspots(patterns: list[LogPattern]) -> HotspotReport:
    """Create a summary report from detected patterns."""
    report = HotspotReport(total_patterns=len(patterns))

    for p in patterns:
        if p.pattern_type.startswith("error:"):
            report.errors += 1
        elif p.pattern_type.startswith("flaky:"):
            report.flaky_signals += 1
        elif p.pattern_type == "perf:cache_hit":
            report.cache_hits += 1
        elif p.pattern_type == "perf:cache_miss":
            report.cache_misses += 1
        elif p.pattern_type.startswith("docker:"):
            report.docker_steps += 1
        elif p.pattern_type == "perf:duration":
            report.duration_mentions += 1

    return report
