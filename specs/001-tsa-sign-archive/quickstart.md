# Quickstart: TSA Sign & Archive CLI

This guide provides runnable validation scenarios to verify the feature works end-to-end.

## Prerequisites

- Python 3.11+ with the project dependencies installed (`uv sync`)
- FFmpeg installed and on PATH (or use `--skip-ffmpeg-meta`)
- A test directory with sample files (videos, images, documents)

## Scenario 1: First-Time Archive (Baseline)

**Goal**: Archive a directory for the first time with TSA timestamps from all 3 Spanish providers.

**Setup**:
```bash
# Create a test directory with sample files
mkdir test_data
echo "Hello, archive!" > test_data/document.txt
# Copy or create some sample media files in test_data/
```

**Run**:
```bash
signed-archive archive --input test_data --output ./output
```

**Expected Result**:
- A `.signed_archive/` folder is created inside `test_data/` containing:
  - `config.yml` (default TSA configuration)
  - `state.json` (run state with hashes and timestamps)
- In `./output/`:
  - `archive_<timestamp>.zip` — ZIP of test_data contents
  - `report_<timestamp>.pdf` — PDF/A-3 report
  - `report_<timestamp>.json` — JSON report with full TSA timestamps (authoritative integrity record)
  - `run_<timestamp>.log` — execution log
- The report contains per-file: SHA-256, MD5, file size, TSA timestamps (3 per file), and any extracted metadata
- The report also contains the archive's own SHA-256 hash

**Verification**:
```bash
signed-archive verify --archive ./output/archive_<timestamp>.zip --report ./output/report_<timestamp>.pdf
```
Expected: `OVERALL: PASS`

---

## Scenario 2: Iterative Update (Add, Modify, Delete)

**Goal**: Add files, modify one, delete one, and verify change detection.

**Setup** (after Scenario 1):
```bash
# Add a new file
echo "New file content" > test_data/new_file.txt

# Modify an existing file
echo "Modified content!" > test_data/document.txt

# Delete a file (if you had more than one)
# rm test_data/some_old_file.txt
```

**Run**:
```bash
signed-archive archive --input test_data --output ./output
```

**Expected Result**:
- In `./output/`:
  - New `archive_<timestamp>.zip` (contains new + modified files; original files not duplicated)
  - New `report_<timestamp>.pdf` (includes original timestamps for unchanged files)
  - `delta_<timestamp>.pdf` — change report listing:
    - `new_file.txt`: ADDED with its hash
    - `document.txt`: MODIFIED (before/after SHA-256 and metadata)
    - `some_old_file.txt`: REMOVED with its previous hash
- `.signed_archive/state.json` is updated with current hashes

---

## Scenario 3: Metadata-Rich Archive

**Goal**: Archive media files (video + image) with full ffprobe-extracted metadata.

**Setup**:
```bash
# Place a video and image in the test dir
# e.g., test_data/sample.mp4, test_data/photo.jpg
```

**Run**:
```bash
signed-archive archive --input test_data --output ./output
```

**Expected Result**:
- Report includes video metadata: duration, frame count, FPS, bitrate, resolution, video codec, audio codec
- Report includes image metadata: format, resolution, pixel format, color space
- All metadata fields populated with values from ffprobe

**Edge case tests**:
```bash
# Test --skip-ffmpeg-meta
signed-archive archive --input test_data --output ./output --skip-ffmpeg-meta
# Should succeed but report shows "no specialized metadata available" for media files

# Test missing ffmpeg (move ffprobe out of PATH or use a system without it)
signed-archive archive --input test_data --output ./output
# Should error: "ffprobe not found. Install ffmpeg or use --skip-ffmpeg-meta"
```

---

## Scenario 4: TSA Server Resilience

**Goal**: Verify the tool continues when a TSA server is unavailable.

**Setup**: Edit `.signed_archive/config.yml` to add a non-existent server:
```yaml
servers:
  - url: http://localhost:19999/fake_tsa
    label: Fake Server (Unreachable)
    enabled: true
  - url: http://tsa.izenpe.com
    label: IZENPE - País Vasco
    enabled: true
```

**Run**:
```bash
signed-archive archive --input test_data --output ./output
```

**Expected Result**:
- Tool retries the fake server (per retry config) then logs failure
- Continues processing and succeeds because at least 1 server (IZENPE) responds
- Run log records: `[WARN] TSA FAIL: Fake Server — connection refused`
- Report lists timestamp from IZENPE; fake server shows status `error`

---

## Scenario 5: Configuration Management

**Goal**: Verify config subcommands work.

**Run**:
```bash
# Show current config
signed-archive config show --input test_data

# Add a custom TSA
signed-archive config add --input test_data "http://custom-tsa.example.com/tsp" "Custom TSA"

# Show again to verify
signed-archive config show --input test_data

# Remove it
signed-archive config remove --input test_data "Custom TSA"

# Reset to defaults
signed-archive config init --input test_data --force
```

**Expected Result**: Each command shows/updates the `.signed_archive/config.yml` correctly.

---

## Scenario 6: Signed Archive with Certificate

**Goal**: Full legal-grade archive with signed ZIP archive.

**Prerequisites**: A valid X.509 certificate (PEM/P12) with private key.

**Run**:
```bash
signed-archive archive \
  --input test_data \
  --output ./output \
  --cert /path/to/certificate.p12 \
  --cert-password "your-password"
```

**Expected Result**:
- A detached signature file `archive_<timestamp>.zip.sig` is created
- Verification command confirms archive integrity:
  ```bash
  signed-archive verify --archive ./output/archive_<timestamp>.zip --report ./output/report_<timestamp>.pdf
  ```
  Expected: `Archive Hash Check: PASS` and all file hashes match

---

## Scenario 7: No Changes Detected

**Goal**: Verify that re-running on unchanged data produces no delta report.

**Run** (immediately after a successful run, without modifying files):
```bash
signed-archive archive --input test_data --output ./output
```

**Expected Result**:
- Console output: "No changes detected since last run."
- No `delta_<timestamp>.pdf` is generated
- No new TSA requests are made (all hashes match previous state)
- `state.json` is NOT updated (run timestamp and run_id remain unchanged if no changes)
- `run_<timestamp>.log` records: "INFO: No changes — skipping archive creation"

---

## Cleanup

```bash
rm -rf test_data ./output
```

## Key Validation Points

1. TSA timestamps from 3 Spanish providers in every report
2. Iterative runs detect added/modified/removed files via hash comparison
3. Original timestamps preserved for unchanged files
4. Delta report lists all changes with before/after hashes
5. Archive hash included in report for self-referential verification
6. `.signed_archive/` folder persists state between runs
7. FFmpeg check errors by default; `--skip-ffmpeg-meta` bypasses
8. Verification command independently validates all TSA timestamps and file hashes
9. TSA server failures don't block the run if minimum servers respond
