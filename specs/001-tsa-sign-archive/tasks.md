# Tasks: TSA Sign & Archive CLI

**Input**: Design documents from `/specs/001-tsa-sign-archive/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Not requested in feature spec. Tasks focus on implementation only.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic package structure

- [X] T001 Create project directory structure: `src/signed_archive/` with subpackages `cli/`, `services/`, `models/`, `config/`, `utils/` and `tests/unit/`, `tests/integration/`, `tests/fixtures/`
- [X] T002 Update `pyproject.toml` with required dependencies: `typer`, `httpx`, `cryptography`, `asn1crypto`, `fpdf2`, `endesive`, `PyYAML`, `portalocker`; add `[project.scripts]` entry point `signed-archive = "signed_archive.cli.main:app"`
- [X] T003 [P] Create `__init__.py` files for all packages: `src/signed_archive/__init__.py`, `src/signed_archive/cli/__init__.py`, `src/signed_archive/services/__init__.py`, `src/signed_archive/models/__init__.py`, `src/signed_archive/config/__init__.py`, `src/signed_archive/utils/__init__.py`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Models (Dataclasses)

- [X] T004 [P] Define `TSAConfiguration` and `TSAServer` dataclasses in `src/signed_archive/models/config.py` (per data-model.md: servers list, min_servers_required, request_timeout, max_retries, retry_backoff, clock_skew_threshold)
- [X] T005 [P] Define `RunState`, `FileRecord`, `TimestampSignature`, `DeltaChange` dataclasses in `src/signed_archive/models/run_state.py` (per data-model.md: run_id, file_records map, tsa_timestamps list, change_type enum, status enums)
- [X] T006 [P] Define `VideoMetadata`, `ImageMetadata`, `DocumentMetadata`, `BasicMetadata` dataclasses in `src/signed_archive/models/metadata.py` (per data-model.md: duration, fps, resolution, codec, color_space, exif, page_count, author)
- [X] T007 [P] Define report rendering model in `src/signed_archive/models/report.py` (aggregation of FileRecords + TimestampSignatures + archive-level hashes/size/count for PDF generation)

### Config & Defaults

- [X] T008 [P] Implement default TSA server list (ACCV, CATCert, IZENPE) and retry policy defaults in `src/signed_archive/config/defaults.py` (per research.md and contracts/cli.md default config.yml)
- [X] T009 [P] Implement config loader with YAML parsing and validation (URL format check, min_servers_required bounds) in `src/signed_archive/config/loader.py`

### Utilities

- [X] T010 [P] Implement file locking wrapper using portalocker in `src/signed_archive/utils/locking.py` (lockfile at `.signed_archive/.lock`, context manager, cross-platform)
- [X] T011 [P] Implement filesystem helpers in `src/signed_archive/utils/fs.py` (recursive directory walk, symlink policy - follow by default with configurable skip, Unicode filename support)
- [X] T012 [P] Implement timing utilities in `src/signed_archive/utils/timing.py` (exponential backoff generator, timeout wrapper)

### Core Services

- [X] T013 [P] Implement streaming SHA-256 and MD5 hasher service in `src/signed_archive/services/hasher.py` (buffer-based streaming for large files, returns dual hashes)
- [X] T014 [P] Implement file-type metadata extraction service in `src/signed_archive/services/metadata.py` (ffprobe subprocess for video/image EXIF; document metadata via stdlib; fallback BasicMetadata for unknown types; classify files as video/image/document/other; handle --skip-ffmpeg-meta flag)
- [X] T015 [P] Implement RFC 3161 TSA client service in `src/signed_archive/services/tsa.py` (build TimeStampReq with asn1crypto, POST via httpx with Content-Type: application/timestamp-query, parse TimeStampResp, extract token + cert info + signing time, retry with exponential backoff per config, concurrent queries via ThreadPoolExecutor)

### Infrastructure

- [X] T016 Set up structured logging infrastructure for run execution logs in `src/signed_archive/services/logger.py` (writes to `run_<ISO8601>.log`, log levels: INFO for progress, WARN for recoverable errors, ERROR for failures per file)
- [X] T017 Implement FFmpeg availability check at startup in `src/signed_archive/utils/fs.py` (check ffprobe via `shutil.which`; error and exit unless `--skip-ffmpeg-meta` flag is set — FR-011a)

**Checkpoint**: Foundation ready — all models, utilities, and core services (hasher, metadata, TSA client, logging, config loader) are in place. User story implementation can now begin.

---

## Phase 3: User Story 1 + 5 — First-Time Archive & Legal Compliance (Priority: P1) 🎯 MVP

**Goal**: Archive a directory for the first time: hash all files, query 3 TSA servers per file, create timestamped ZIP archive, generate signed PDF/A-3 report with all hashes/timestamps/metadata, with outputs meeting eIDAS legal compliance standards.

**US1 Independent Test**: Run `signed-archive archive --input <dir> --output <out> --no-sign` against any directory of mixed media files. Verify: ZIP archive created, PDF/A-3 report generated with per-file SHA-256/MD5/TSA timestamps/metadata, archive hash in report, run log produced.

**US5 Independent Test**: A third-party auditor verifies timestamps come from qualified eIDAS providers (EUTL), report conforms to PDF/A-3 for long-term preservation, signatures follow PAdES-BASELINE-LT and CAdES standards with embedded certificate chains.

### Implementation

- [X] T018 [P] [US1] Implement ZIP archiver service in `src/signed_archive/services/archiver.py` (streaming ZIP creation preserving directory structure, original file modification times, ZIP64 for >4GB, Unicode filenames)
- [X] T019 [P] [US1] Implement PDF/A-3 report generation in `src/signed_archive/services/reporter.py` (using fpdf2 with PDF/A-3 conformance: XMP metadata, embedded fonts, sRGB color profile; render per-file table with filename, relative path, size, SHA-256, MD5, type-specific metadata, TSA timestamps per server; include archive-level metadata: ZIP SHA-256, MD5, size, file count; generate archive hash after ZIP creation for self-referential integrity — FR-009, FR-010)
- [X] T020 [US1] Implement PAdES-BASELINE-LT PDF signing in `src/signed_archive/services/signer.py` (using endesive + cryptography; sign report PDF with user-provided X.509 certificate; embed full certificate chain and revocation data (CRL/OCSP) for long-term validation — FR-014, SC-005)
- [X] T021 [US1] Implement CAdES detached ZIP signing in `src/signed_archive/services/signer.py` (using cryptography CMS + asn1crypto; create detached signature file `.zip.sig` with ESS signing-certificate attributes; sign archive hash — FR-015)
- [X] T022 [US1] Implement run orchestration pipeline in `src/signed_archive/cli/archive.py` (walk directory → hash files → classify types → extract metadata → query TSA servers concurrently → create ZIP → compute archive hash → generate report → sign report + archive → write state.json → write run log)
- [X] T023 [US1] Implement CLI archive subcommand in `src/signed_archive/cli/archive.py` (typer command with all flags per contracts/cli.md: --input, --output, --cert, --cert-key, --cert-password, --tsa-config, --skip-ffmpeg-meta, --max-retries, --timeout, --no-sign, --dry-run; ffmpeg availability check with error/exit unless --skip-ffmpeg-meta; config auto-generation on first run; exit codes 0/1/2)
- [X] T024 [US1] Implement main CLI entry point in `src/signed_archive/cli/main.py` (typer app with --version, --help; register archive subcommand; load env vars with CLI flag override per contracts/cli.md)
- [X] T025 [US1] Implement output file naming with ISO 8601 UTC timestamps (`archive_<TS>.zip`, `archive_<TS>.zip.sig`, `report_<TS>.pdf`, `run_<TS>.log`) and first-run state.json writing to `.signed_archive/state.json`
- [X] T026 [US1] Implement per-file error resilience (FR-032): catch read/perm errors per file, log and continue, mark file as skipped in report, aggregate errors for final exit code
- [X] T027 [US5] Ensure multi-TSA minimum requirement enforcement in archive pipeline: validate at least `min_servers_required` TSA servers respond per file; flag files below threshold in report and exit code (FR-003, FR-005)
- [X] T028 [US5] Add TSA certificate chain extraction and storage in TimestampSignature (extract TSA cert subject/issuer/serial from TimeStampToken for independent verification — FR-004)
- [X] T029 [US5] Validate generated PDF/A-3 conformance: embed proper XMP metadata stream (dc:title, dc:creator, xmp:CreateDate, pdfaid:part=3, pdfaid:conformance=A), sRGB IEC61966-2.1 output intent, fully embedded fonts; ensure fpdf2 PDF/A-3 mode is active
- [X] T030 [US1] Implement `--dry-run` mode: compute hashes and metadata only, report results to stdout, skip TSA queries/ZIP/report generation

**Checkpoint**: User Story 1 + 5 complete. First-time archive creation fully functional with eIDAS-compliant signed outputs.

---

## Phase 4: User Story 2 — Iterative Archive Update & Change Detection (Priority: P2)

**Goal**: On subsequent runs, detect added/modified/removed files via hash comparison against previous state; only timestamp and archive new/changed files; generate delta change report; preserve original TSA timestamps for unchanged files.

**Independent Test**: Run initial archive, then add/remove/modify files in the directory, run again. Verify: new files get timestamps and added to ZIP, modified/removed files flagged in delta report with before/after hashes, unchanged files retain original timestamps.

### Implementation

- [X] T031 [P] [US2] Implement previous state loading and hash-based comparison logic in `src/signed_archive/services/archiver.py` (load state.json, compare file_records keys and SHA-256 hashes against current filesystem; identify added/removed/modified/metadata_changed per data-model.md validation rules)
- [X] T032 [P] [US2] Implement DeltaChange collection in `src/signed_archive/services/archiver.py` (populate change_type, before/after hashes, before/after metadata snapshots, carry-forward original TSA timestamps for unchanged files — FR-016, FR-017, FR-018, FR-020)
- [X] T033 [US2] Implement iterative ZIP archiving in `src/signed_archive/services/archiver.py` (add only new/modified files to ZIP, skip unchanged, preserve existing ZIP content, compute new archive hash for report — FR-007)
- [X] T034 [US2] Implement delta report PDF/A-3 generation in `src/signed_archive/services/reporter.py` (render change summary: added files with new hashes, modified files with before/after hashes+metadata, removed files with previous hash, metadata-only changes; format matching delta_<TS>.pdf output — FR-019)
- [X] T035 [US2] Integrate iterative mode into archive CLI pipeline in `src/signed_archive/cli/archive.py` (detect existing state.json → if present, run comparison; if no changes detected, log "no changes" and skip archive/delta generation per quickstart Scenario 7; if state.json missing/corrupt, warn and treat as first run per FR acceptance scenario 3)
- [X] T036 [US2] Handle edge cases: corrupted/missing previous state (warn user, fallback to first-time run), config hash mismatch between runs (warn), preserve original timestamps in iterative report header with reference to original signing time
- [X] T037 [US2] Update state.json on iterative runs: merge new FileRecords for added/modified files, remove entries for deleted files, carry forward unchanged entries, update run_id and run_timestamp

**Checkpoint**: User Story 2 complete. Iterative archiving with full change detection and delta reporting functional.

---

## Phase 5: User Story 3 — TSA Server Configuration (Priority: P2)

**Goal**: Provide config management subcommands to view, add, remove TSA servers and initialize/reset default configuration. Validate configuration at startup.

**Independent Test**: Use `signed-archive config add/remove/show/init` to manage TSA servers; verify archive command uses updated config. Test validation rejects malformed URLs.

### Implementation

- [X] T038 [P] [US3] Implement `config init` subcommand in `src/signed_archive/cli/config.py` (generate default config.yml with 3 Spanish TSA providers in `.signed_archive/` per contracts/cli.md; --force flag to overwrite; create `.signed_archive/` directory if missing)
- [X] T039 [P] [US3] Implement `config show` subcommand in `src/signed_archive/cli/config.py` (load and display current YAML config as formatted output; show server list with enabled status, retry policy values)
- [X] T040 [US3] Implement `config add` subcommand in `src/signed_archive/cli/config.py` (add TSA server by URL + LABEL arguments; optional --certificate-url; append to servers list; validate URL format before adding — FR-023)
- [X] T041 [US3] Implement `config remove` subcommand in `src/signed_archive/cli/config.py` (remove TSA server by matching URL or label IDENTIFIER argument; error if not found)
- [X] T042 [US3] Implement config validation on load in `src/signed_archive/config/loader.py` (validate all server URLs are well-formed HTTP/HTTPS; validate min_servers_required >= 1 and <= count of enabled servers; reject with clear error per FR-023, FR acceptance scenario 3)
- [X] T043 [US3] Register config subcommand group in `src/signed_archive/cli/main.py` (typer group with init/show/add/remove subcommands; register on main app)

**Checkpoint**: User Story 3 complete. TSA server configuration fully manageable via CLI.

---

## Phase 6: User Story 4 — Report & Archive Verification (Priority: P3)

**Goal**: Provide a verification subcommand that independently validates archive integrity, report signature, per-file hash matching, and TSA timestamp cryptographic validity. Output human-readable or JSON report.

**Independent Test**: Run `signed-archive verify --archive <zip> --report <pdf>` on a previously created archive+report pair. Verify: confirms all hashes match, signatures valid, timestamps cryptographically verified. Tamper with a file in the ZIP and verify it detects the mismatch.

### Implementation

- [X] T044 [P] [US4] Implement archive integrity verification in `src/signed_archive/services/verifier.py` (FR-026: for each file in the report, extract corresponding file from ZIP, compute SHA-256, compare against report hash; report per-file PASS/FAIL)
- [X] T045 [P] [US4] Implement TSA timestamp cryptographic verification in `src/signed_archive/services/verifier.py` (FR-027: parse stored TimeStampToken, verify signature with TSA certificate public key, verify hash matches file; handle expired cert with timestamp-time comparison per acceptance scenario 3)
- [X] T046 [P] [US4] Implement PAdES report signature verification in `src/signed_archive/services/verifier.py` (FR-028: verify report's embedded digital signature using endesive; extract signer identity, signing time; validate signature integrity)
- [X] T047 [US4] Implement verify CLI subcommand in `src/signed_archive/cli/verify.py` (per contracts/cli.md: --archive, --report required flags; --verify-tsa-certs for EUTL check; --output file; --format text|json; exit codes 0/1/2)
- [X] T048 [US4] Implement verification report output formatting in `src/signed_archive/cli/verify.py` (text format: ascii table per contracts/cli.md with Archive Hash Check, Report Signature Check, File Integrity Check, TSA Timestamp Check, OVERALL; JSON format: matching schema per contracts/cli.md)
- [X] T049 [US4] Register verify subcommand in `src/signed_archive/cli/main.py`

**Checkpoint**: User Story 4 complete. Independent verification of all archive outputs functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and ensure robustness.

- [X] T050 [P] Handle edge cases: empty directory (produce valid report noting "no files to archive", exit cleanly), Unicode filenames in ZIP/reports (FR-034), symlink policy (follow by default, skip if configured)
- [X] T051 [P] Implement environment variable support (`SIGNED_ARCHIVE_CERT`, `SIGNED_ARCHIVE_CERT_KEY`, `SIGNED_ARCHIVE_CERT_PASSWORD`, `SIGNED_ARCHIVE_TSA_CONFIG`, `SIGNED_ARCHIVE_SKIP_FFMPEG`) in archive command per contracts/cli.md
- [X] T052 [P] Implement concurrent run prevention: acquire file lock at `.signed_archive/.lock` on archive start, release on exit; fail with clear error if lock held (FR-035)
- [X] T053 Perform streaming I/O audit: ensure hasher, archiver, and TSA client use buffer-based streaming for files >10MB to stay within 512MB RAM (FR-033, SC-007)
- [X] T054 Implement concurrent TSA queries via ThreadPoolExecutor (query all enabled TSA servers per file in parallel with configurable timeout) to meet performance goal (SC-001: <5 min for 1,000 files)
- [X] T055 Add TSA timestamp clock skew flagging: if timestamps from different servers for same file differ by >5 seconds, log WARN in run log (Edge Cases spec)
- [X] T056 Run quickstart.md validation scenarios end-to-end (Scenarios 1-7) to verify all acceptance criteria pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (project structure exists) — BLOCKS all user stories
- **US1+US5 (Phase 3)**: Depends on Phase 2 — Core MVP
- **US2 (Phase 4)**: Depends on Phase 3 (needs archiver, reporter, models for change detection)
- **US3 (Phase 5)**: Depends on Phase 2 — Can start after Foundational; independent of US1
- **US4 (Phase 6)**: Depends on Phase 3 (needs signed reports/archives to verify)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKS ALL)
    ↓
    ├── Phase 3: US1+US5 (P1) ← MVP, must complete first
    │       ↓
    ├── Phase 4: US2 (P2) ← Depends on US1 (archiver, reporter)
    │
    ├── Phase 5: US3 (P2) ← Independent after Phase 2
    │
    └── Phase 6: US4 (P3) ← Depends on US1 (needs outputs to verify)
            ↓
Phase 7: Polish
```

- **US3 (Config)** can be built in parallel with US1 after Phase 2
- **US2 (Iterative)** naturally depends on US1's archiver and reporter
- **US4 (Verify)** naturally depends on US1's signed outputs

### Within Each Phase

- All tasks marked [P] can run in parallel
- Models before services (within a phase)
- Services before CLI integration
- Core implementation before edge cases

---

## Parallel Execution Examples

### Phase 2: Foundational (maximum parallelism)

```bash
# These can ALL run in parallel (different files, no inter-dependencies):
Task: "Define TSAConfiguration and TSAServer dataclasses in src/signed_archive/models/config.py"
Task: "Define RunState, FileRecord, TimestampSignature dataclasses in src/signed_archive/models/run_state.py"
Task: "Define VideoMetadata, ImageMetadata, DocumentMetadata dataclasses in src/signed_archive/models/metadata.py"
Task: "Define report rendering model in src/signed_archive/models/report.py"
Task: "Implement default TSA server list in src/signed_archive/config/defaults.py"
Task: "Implement file locking wrapper in src/signed_archive/utils/locking.py"
Task: "Implement filesystem helpers in src/signed_archive/utils/fs.py"
Task: "Implement timing utilities in src/signed_archive/utils/timing.py"
Task: "Implement hasher service in src/signed_archive/services/hasher.py"
Task: "Implement metadata extraction service in src/signed_archive/services/metadata.py"
Task: "Implement RFC 3161 TSA client in src/signed_archive/services/tsa.py"
```

### Phase 3: US1+US5

```bash
# These can run in parallel:
Task: "Implement ZIP archiver service in src/signed_archive/services/archiver.py"
Task: "Implement PDF/A-3 report generation in src/signed_archive/services/reporter.py"

# Then sequentially (signer depends on PDF report, CLI depends on all services):
Task: "Implement PAdES + CAdES signing in src/signed_archive/services/signer.py"
Task: "Implement archive CLI subcommand + pipeline in src/signed_archive/cli/archive.py"
Task: "Implement main CLI entry point in src/signed_archive/cli/main.py"
```

### Phase 5: US3 (parallel within)

```bash
# These can run in parallel:
Task: "Implement config init subcommand in src/signed_archive/cli/config.py"
Task: "Implement config show subcommand in src/signed_archive/cli/config.py"

# Then sequentially:
Task: "Implement config add/remove subcommands in src/signed_archive/cli/config.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 5 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 + US5 (First-Time Archive + Legal Compliance)
4. **STOP and VALIDATE**: Test with `signed-archive archive --input <dir> --output <out> --no-sign`
5. Verify: ZIP created, PDF/A-3 report with hashes/timestamps/metadata, run log
6. Deploy/demo if ready — this provides a working, legally-compliant archiving tool

### Incremental Delivery

1. Phase 1-2 → Foundation ready
2. Phase 3 (US1+US5) → First-time archive with legal compliance → **MVP!**
3. Phase 4 (US2) → Iterative updates with change detection → **Enhanced MVP**
4. Phase 5 (US3) → TSA config management → **Configurable**
5. Phase 6 (US4) → Independent verification → **Fully auditable**
6. Phase 7 (Polish) → Production-ready robustness

### Parallel Team Strategy

With multiple developers:
1. Team completes Phase 1 + 2 together (foundation)
2. Once Phase 2 is done:
   - Developer A: Phase 3 (US1+US5) — Core archive pipeline
   - Developer B: Phase 5 (US3) — Config management (independent of US1)
3. After Phase 3: Developer A continues to Phase 4 (US2), Developer B to Phase 6 (US4)
4. Team collaborates on Phase 7 (Polish)

---

## Summary

| Phase | User Stories | Task Count | Independent Test |
|-------|-------------|------------|------------------|
| Phase 1: Setup | — | 3 | Package installs, imports work |
| Phase 2: Foundational | — | 14 | All models, utils, services importable |
| Phase 3: US1+US5 (P1) | First-Time Archive & Legal Compliance | 13 | `archive --no-sign` produces ZIP + report + log |
| Phase 4: US2 (P2) | Iterative Update & Change Detection | 7 | Second run detects added/removed/modified files |
| Phase 5: US3 (P2) | TSA Server Configuration | 6 | `config add/remove/show/init` works end-to-end |
| Phase 6: US4 (P3) | Report & Archive Verification | 6 | `verify --archive --report` validates all checks |
| Phase 7: Polish | Cross-Cutting | 7 | Quickstart scenarios 1-7 all pass |
| **Total** | **5 stories** | **56** | |

### MVP Scope

**MVP = Phase 1 + 2 + 3** (30 tasks): A working CLI tool that archives a directory with 3 TSA timestamp servers, generates a signed PDF/A-3 report, and produces a timestamped ZIP archive — fully eIDAS-compliant for Spanish legal use.

### Format Validation

All 56 tasks follow the strict checklist format: `- [ ] [TaskID] [P?] [Story?] Description with file path`.
