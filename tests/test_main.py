"""Tests for atlas-log-analyzer __main__ entry point."""

import json
import subprocess
import sys
import tempfile
import os


def _run(*args, stdin_data=None):
    """Run atlas_log_analyzer module with given args, return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "atlas_log_analyzer", *args],
        capture_output=True,
        text=True,
        input=stdin_data,
        timeout=15,
    )
    return result.returncode, result.stdout, result.stderr


class TestMain:
    def test_help_exits_zero(self):
        code, _, _ = _run("--help")
        assert code == 0

    def test_empty_stdin_produces_json(self):
        code, out, _ = _run(stdin_data="")
        assert code == 0
        data = json.loads(out)
        assert "total_patterns" in data
        assert data["total_patterns"] == 0

    def test_oom_log_detected(self):
        code, out, _ = _run(stdin_data="Build step failed\nOut of memory: Kill process 1234\nBuild done")
        assert code == 0
        data = json.loads(out)
        assert data["errors"] >= 1

    def test_cache_hit_detected(self):
        code, out, _ = _run(stdin_data="cache hit for node_modules\nRunning tests...")
        assert code == 0
        data = json.loads(out)
        assert data["cache_hits"] >= 1

    def test_verbose_includes_patterns(self):
        code, out, _ = _run("--verbose", stdin_data="error: something failed")
        assert code == 0
        data = json.loads(out)
        assert "patterns" in data
        assert len(data["patterns"]) > 0

    def test_file_flag_reads_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as f:
            f.write("connection refused\nerror: build failed\n")
            fname = f.name
        try:
            code, out, _ = _run("--file", fname)
            assert code == 0
            data = json.loads(out)
            assert data["errors"] >= 1
        finally:
            os.unlink(fname)

    def test_missing_file_exits_nonzero(self):
        code, _, _ = _run("--file", "/nonexistent/path/build.log")
        assert code != 0
