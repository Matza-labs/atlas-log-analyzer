"""Unit tests for atlas-log-analyzer — pattern extraction and hotspot analysis."""

import pytest

from atlas_log_analyzer.patterns import LogPattern, HotspotReport, analyze_log, summarize_hotspots

SAMPLE_LOG = """
Step 1/5: Checking out code
Cloning repository...
Step 2/5: Installing dependencies
Downloading node_modules: 125 MB
npm install completed in 45.2 seconds
Cache miss: node_modules not found in cache
Step 3/5: Running tests
test_auth.py::test_login PASSED
test_auth.py::test_signup FAILED - Connection refused
Retrying test_auth.py::test_signup... attempt 2 of 3
test_auth.py::test_signup PASSED
Step 4/5: Building Docker image
Step 1/8: FROM node:18-alpine
Step 2/8: COPY package.json .
---> Using cache
Step 3/8: RUN npm ci
Step 4/8: COPY . .
Step 5/8: RUN npm run build
Build completed in 120 seconds
Successfully built a1b2c3d4
Step 5/5: Deploying
Error: Permission denied when pushing to registry
Fatal: deployment failed
"""


class TestLogPatterns:

    def test_analyze_log_detects_errors(self):
        patterns = analyze_log(SAMPLE_LOG)
        error_patterns = [p for p in patterns if p.pattern_type.startswith("error:")]
        assert len(error_patterns) >= 2
        # Should detect network error (connection refused) and permission error
        types = {p.pattern_type for p in error_patterns}
        assert "error:network" in types
        assert "error:permission" in types

    def test_analyze_log_detects_flaky(self):
        patterns = analyze_log(SAMPLE_LOG)
        flaky_patterns = [p for p in patterns if p.pattern_type.startswith("flaky:")]
        assert len(flaky_patterns) >= 1
        assert any(p.pattern_type == "flaky:retry" for p in flaky_patterns)

    def test_analyze_log_detects_performance(self):
        patterns = analyze_log(SAMPLE_LOG)
        perf_patterns = [p for p in patterns if p.pattern_type.startswith("perf:")]
        assert len(perf_patterns) >= 2
        # Cache miss
        assert any(p.pattern_type == "perf:cache_miss" for p in perf_patterns)
        # Duration
        assert any(p.pattern_type == "perf:duration" for p in perf_patterns)

    def test_analyze_log_detects_docker(self):
        patterns = analyze_log(SAMPLE_LOG)
        docker_patterns = [p for p in patterns if p.pattern_type.startswith("docker:")]
        assert len(docker_patterns) >= 2
        assert any(p.pattern_type == "docker:docker_cache" for p in docker_patterns)
        assert any(p.pattern_type == "docker:docker_built" for p in docker_patterns)

    def test_analyze_empty_log(self):
        patterns = analyze_log("")
        assert patterns == []

    def test_analyze_clean_log(self):
        patterns = analyze_log("Everything is fine.\nAll steps completed successfully.\n")
        # Should find no significant patterns
        error_patterns = [p for p in patterns if p.pattern_type.startswith("error:")]
        assert len(error_patterns) == 0

    def test_line_numbers_set(self):
        patterns = analyze_log(SAMPLE_LOG)
        for p in patterns:
            assert p.line_number is not None
            assert p.line_number > 0


class TestHotspotReport:

    def test_summarize_hotspots(self):
        patterns = analyze_log(SAMPLE_LOG)
        report = summarize_hotspots(patterns)

        assert isinstance(report, HotspotReport)
        assert report.total_patterns == len(patterns)
        assert report.errors >= 2
        assert report.flaky_signals >= 1
        assert report.cache_misses >= 1
        assert report.docker_steps >= 2
        assert report.duration_mentions >= 1
