# atlas-log-analyzer

Runtime Analysis Engine for **PipelineAtlas** — build log intelligence.

## Purpose

Extracts dynamic behavior from CI/CD build logs that can't be detected statically. Uses deterministic regex-first pattern matching.

## Status: 🟢 Complete (Phase 3)

This service is fully implemented as part of Phase 3. It runs as a stream consumer (`--mode stream`).

## Planned Features

- Build log retrieval from CI platforms
- Log sanitization (ANSI strip, secret redaction)
- Stage-level log chunking
- Regex-based pattern extraction (execution order, sub-builds, docker builds, errors, retries)
- Performance metric extraction

## Dependencies

- `atlas-sdk` (shared models)
- `redis` (Redis Streams)

## Related Services

Receives from ← `atlas-scanner` (via Redis Streams)
Publishes to → `atlas-graph`
