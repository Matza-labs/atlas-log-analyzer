# atlas-log-analyzer

Runtime Analysis Engine for **PipelineAtlas** — build log intelligence.

## Purpose

Extracts dynamic behavior from CI/CD build logs that can't be detected statically. Uses deterministic regex-first pattern matching.

## Status: 🟡 Phase 2

This service is planned for Phase 2. The directory structure is scaffolded and ready for implementation.

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
