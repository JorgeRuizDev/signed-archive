# Research: TSA Sign & Archive CLI

**Date**: 2026-07-29

## Decision Log

### 1. RFC 3161 TSA Client Implementation

**Decision**: Custom implementation using `asn1crypto` for ASN.1 structures and `httpx` for HTTP transport.

**Rationale**: No mature, maintained Python library exists specifically for RFC 3161 TSA client operations. The protocol is straightforward:
1. Build a `TimeStampReq` ASN.1 structure (hash algorithm OID + hash value + optional nonce)
2. POST it to the TSA server URL with `Content-Type: application/timestamp-query`
3. Parse the `TimeStampResp` ASN.1 response (status + optional `TimeStampToken`)

The `asn1crypto` library provides the necessary ASN.1 definitions for PKCS/PKIX structures including `TimeStampReq`, `TimeStampResp`, and `TimeStampToken`. `httpx` provides HTTP/1.1 transport with timeout and retry support.

**Alternatives considered**:
- `rfc3161-client` (PyPI) — unmaintained, last release 2017, does not support Python 3.11+
- `pyopenssl` + manual DER construction — more verbose than `asn1crypto`, less type-safe
- OpenSSL CLI via subprocess — fragile, platform-dependent output parsing

### 2. PDF/A-3 Generation

**Decision**: `fpdf2` for PDF generation with PDF/A-3 conformance.

**Rationale**: `fpdf2` (successor to `fpdf`) natively supports PDF/A-3 generation with proper metadata XMP streams, color profiles, and font embedding. It is actively maintained, has clean API for programmatic PDF construction (tables, text, metadata), and is lightweight compared to `reportlab`.

**Alternatives considered**:
- `reportlab` — more powerful but heavier; PDF/A support requires manual configuration; API is more complex for report-style documents
- `weasyprint` (HTML → PDF) + Ghostscript PDF/A conversion — two-step process adds complexity and external dependencies
- `pikepdf` — excellent for manipulating existing PDFs but not for generating from scratch

### 3. Report Generation

**Decision**: The PDF report is generated unsigned; integrity is established through the JSON report's embedded TSA timestamps.

**Rationale**: The JSON report contains full cryptographic hashes and RFC 3161 timestamp tokens that serve as the authoritative integrity record. This avoids the complexity of PAdES-based PDF signing while maintaining legal-grade timestamp proof via the TSA servers. The JSON output is machine-parseable and can be independently verified by third parties.

**Alternatives considered**:
- `endesive` for PAdES baseline signatures — removed to simplify the tool; PDF signatures are redundant when every file and the archive already have TSA timestamps in the JSON report
- `pyHanko` — also supports PAdES but primarily focused on Belgian eID; heavier dependency chain
- Manual PKCS#7/CMS construction for PDF — extremely complex and error-prone for PDF incremental updates

### 4. CAdES Detached Signature for ZIP Archives

**Decision**: `cryptography` library's `cms` module for CMS SignedData with CAdES enhancements.

**Rationale**: CAdES (CMS Advanced Electronic Signatures) is an extension of CMS (Cryptographic Message Syntax, RFC 5652). A detached signature contains the signed attributes (signing-certificate, signing-time, content-type, message-digest) and the signature value, referencing the external data (the ZIP archive) by hash.

The `cryptography` library's `cms` module provides building blocks for CMS structures. For CAdES enhancements (ESS signing-certificate attribute, TSA timestamp), additional ASN.1 attributes are added using `asn1crypto`.

**Alternatives considered**:
- `pyopenssl` — does not expose CMS/CAdES operations
- OpenSSL CLI `openssl cms -sign` — works but requires temporary files and subprocess management

### 5. FFmpeg / ffprobe Metadata Extraction

**Decision**: Subprocess call to `ffprobe` with JSON output for video/image metadata.

**Rationale**: `ffprobe` is the standard tool for multimedia metadata extraction and is bundled with FFmpeg. The JSON output format (`-print_format json -show_format -show_streams`) is machine-parseable and comprehensive.

Python wrappers like `ffmpeg-python` add complexity without significant benefit — they merely construct ffprobe command lines. Direct subprocess with `json.loads()` on stdout is simpler and equally effective.

**Key ffprobe fields extracted**:
- Video: `duration`, `nb_frames`, `r_frame_rate`, `bit_rate`, `width`, `height`, `codec_name`, audio codec from streams
- Image: `width`, `height`, `codec_name` (format), `bits_per_raw_sample`, `color_space`, `pix_fmt`

**Availability check**: `shutil.which("ffprobe")` or `subprocess.run(["ffprobe", "-version"])` to detect availability.

### 6. CLI Framework

**Decision**: `typer` (already in virtual environment).

**Rationale**: `typer` is already installed (used by `specify-cli`). It builds on `click` and provides automatic help text generation, type validation, and clean error messages. Native async support (`asyncio`) is not needed since TSA requests can run concurrently via `concurrent.futures` with `httpx`.

**Alternatives considered**:
- `click` — the foundation; typer's wrapper adds type hints and cleaner API
- `argparse` — stdlib but verbose for multi-subcommand CLIs

### 7. Configuration Storage

**Decision**: YAML for config (`config.yml`), JSON for run state (`state.json`).

**Rationale**:
- YAML is human-readable and editable; ideal for TSA server URLs and retry policies (FR-022)
- JSON is machine-optimal for the state file (FR-021a) — deterministic serialization ensures hash stability for comparison

Both files live in `.signed_archive/` inside the input directory.

**Alternatives considered**:
- TOML — Python's `tomllib` (3.11+) supports it but YAML is more common for server lists with comments
- INI — too flat for nested TSA server configuration with retry parameters

### 8. Python 3.11+ Language Features

**Decision**: Adopt modern Python features available in 3.11+.

**Rationale**: The project requires Python >=3.11 per `pyproject.toml`. This enables:
- `tomllib` for reading TOML (unused, but available)
- `Self` type for class methods returning instances
- `ExceptionGroup` / `except*` for aggregating multiple file errors
- `asyncio.TaskGroup` (3.11) if async TSA queries are added later
- `functools.cached_property` for lazy computation of hashes

### 9. File Locking

**Decision**: `portalocker` for cross-platform advisory file locking.

**Rationale**: Prevents corruption from concurrent runs against the same directory (FR-035). `portalocker` provides a unified API over Windows `msvcrt` locking and Unix `fcntl` locking. The lock file is `.signed_archive/.lock`.

**Alternatives considered**:
- `filelock` — also viable; `portalocker` chosen for its lighter weight and explicit cross-platform guarantees
- Manual `msvcrt`/`fcntl` — unnecessary platform-specific code

### 10. Default TSA Server List

**Decision**: Three qualified Spanish TSA providers as specified by the user.

The three servers are all eIDAS-qualified providers under the EU Trusted List (EUTL):

| Provider | Region | URL | Protocol | Auth |
|----------|--------|-----|----------|------|
| ACCV (ISTEC) | Comunidad Valenciana | `http://tss.accv.es:8318/tsa` | RFC 3161 over HTTP | Open for testing; professional use requires credentials |
| CATCert | Catalunya | `http://psis.catcert.net/psis/catcert/tsp` | RFC 3161 over HTTP | Open (no auth) |
| IZENPE | País Vasco | `http://tsa.izenpe.com` | RFC 3161 over HTTP | Open (no auth) |

All three are checked on every run. At least one must respond (configurable minimum, default: 1).
