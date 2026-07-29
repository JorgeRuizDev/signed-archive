# Implementation Plan: TSA Sign & Archive CLI

**Branch**: `001-tsa-sign-archive` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-tsa-sign-archive/spec.md`

## Summary

Build a Python CLI tool that timestamps files using 3 qualified Spanish TSA providers (ACCV, CATCert, IZENPE) via RFC 3161, archives them into a timestamped ZIP, and generates eIDAS-compliant signed PDF/A-3 reports with full file metadata. Video/image metadata is extracted via ffprobe (FFmpeg). Iterative runs detect changes (added/removed/modified files) via hash-based comparison stored in `.signed_archive/state.json`. The tool targets legal validity in Spain under EU eIDAS Regulation 910/2014.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**:
- `typer` — CLI framework (already in venv)
- `httpx` — async HTTP client for TSA server requests (RFC 3161 over HTTP)
- `cryptography` — X.509 certificate handling, CMS/CAdES signing, cryptographic primitives
- `asn1crypto` — ASN.1 parsing/building for RFC 3161 TimeStampReq/TimeStampResp structures
- `fpdf2` — PDF/A-3 generation for reports
- `endesive` — PAdES baseline signatures on PDF reports
- `PyYAML` — YAML configuration file parsing
- `portalocker` — cross-platform file locking
- `ffmpeg` (system dependency) — video/image metadata extraction via `ffprobe` subprocess

**Storage**: Filesystem
- `.signed_archive/config.yml` — TSA configuration (in --input directory)
- `.signed_archive/state.json` — previous run hashes and metadata for change detection
- `<output>/archive_<ISO8601>.zip` — timestamped ZIP archive
- `<output>/archive_<ISO8601>.zip.sig` — detached CAdES signature for archive
- `<output>/report_<ISO8601>.pdf` — signed PDF/A-3 report
- `<output>/delta_<ISO8601>.pdf` — delta change report (iterative runs only)
- `<output>/run_<ISO8601>.log` — run execution log

**Testing**: pytest

**Target Platform**: Windows (primary), macOS, Linux

**Project Type**: CLI tool (single package)

**Performance Goals**:
- 1,000 files processed in <5 minutes with 3 TSA servers
- 10GB single file streamed without exceeding 512MB RAM
- TSA request timeout: 30s per server, 3 retries with exponential backoff

**Constraints**:
- PDF/A-3 compliance (validated by standards-compliant PDF/A conformance checker)
- RFC 3161 compliant TSA communication
- PAdES BASELINE-B/LT signature levels
- CAdES detached signature for ZIP archives
- Streaming I/O for large files (no full-file buffering)
- File locking to prevent concurrent-run corruption
- Unicode filename support on all platforms

**Scale/Scope**:
- 3 TSA servers by default
- Single directory per run, recursive subdirectory processing
- Iterative runs: compare current vs. previous state
- Supported deep metadata: MP4, MOV, AVI, MKV (video); JPEG, PNG, TIFF, GIF, BMP, WebP (images); PDF, DOCX, ODT (documents)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution (`.specify/memory/constitution.md`) is in template state — no principles have been defined. No gates apply. The following principles are adopted for this feature:

| Principle | Commitment |
|-----------|-----------|
| **CLI-First** | Every operation exposed via CLI subcommands with clear args/flags; human-readable stderr for errors, stdout for results |
| **Streaming-First** | All I/O operations on files >10MB use streaming/buffered processing to minimize memory |
| **Fail-Safe** | Individual file failures do not abort the entire run; errors are logged and aggregated |
| **Verifiable Outputs** | All outputs (reports, timestamps, signatures) must be independently verifiable without the tool |

## Project Structure

### Documentation (this feature)

```text
specs/001-tsa-sign-archive/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output — CLI API specification
│   └── cli.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/signed_archive/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py          # Typer app entry point
│   ├── archive.py       # "archive" subcommand
│   ├── verify.py        # "verify" subcommand
│   └── config.py        # "config" subcommand
├── services/
│   ├── __init__.py
│   ├── hasher.py        # SHA-256, MD5 streaming hashing
│   ├── tsa.py           # RFC 3161 TSA client (TimeStampReq → TimeStampResp)
│   ├── archiver.py      # ZIP archive creation (iterative)
│   ├── signer.py        # PAdES (report) + CAdES (archive) signing
│   ├── metadata.py      # File-type-specific metadata extraction (ffprobe + fallbacks)
│   └── verifier.py      # Report + archive verification logic
├── models/
│   ├── __init__.py
│   ├── run_state.py     # RunState, FileRecord, TimestampSignature dataclasses
│   ├── config.py        # TSA configuration model
│   └── report.py        # Report rendering model
├── config/
│   ├── __init__.py
│   └── defaults.py      # Default TSA servers, retry policy, etc.
└── utils/
    ├── __init__.py
    ├── locking.py       # File locking wrapper (portalocker)
    ├── fs.py            # Filesystem helpers (recursive walk, symlink policy)
    └── timing.py        # Exponential backoff, timeout helpers

tests/
├── conftest.py
├── unit/
│   ├── test_hasher.py
│   ├── test_tsa.py
│   ├── test_metadata.py
│   ├── test_config.py
│   └── test_models.py
├── integration/
│   ├── test_archive_flow.py
│   ├── test_iterative_flow.py
│   ├── test_verification.py
│   └── test_error_handling.py
└── fixtures/
    ├── sample_video.mp4
    ├── sample_image.jpg
    └── sample_doc.pdf
```

**Structure Decision**: Single Python package (`src/signed_archive`) with layered architecture: CLI layer → Services layer → Models layer → Utils layer. This follows the Python project convention and keeps the tool self-contained. Tests mirror the source structure with unit and integration separation.

## Complexity Tracking

> No constitution violations. No complexity tracking needed.

No violations — the project fits within a single Python package with layered separation of concerns. No additional projects, frameworks, or patterns are required.
