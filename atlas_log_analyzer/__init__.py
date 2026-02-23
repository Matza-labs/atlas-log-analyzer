"""PipelineAtlas Log Analyzer — runtime log intelligence."""

__version__ = "0.1.0"

from atlas_log_analyzer.patterns import (  # noqa: F401
    LogPattern,
    HotspotReport,
    analyze_log,
    summarize_hotspots,
)
