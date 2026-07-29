# Data Model: TSA Sign & Archive CLI

## Entities

### RunState

The top-level state object stored in `.signed_archive/state.json`. Contains the snapshot of the last successful run, used for change detection on iterative runs.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | UUID4 of this run |
| `run_timestamp` | `str` (ISO 8601) | When the run executed |
| `input_directory` | `str` | Absolute path of the --input directory |
| `archive_sha256` | `str` (hex) | SHA-256 of the generated ZIP archive |
| `archive_md5` | `str` (hex) | MD5 of the generated ZIP archive |
| `archive_size` | `int` | Size of the ZIP archive in bytes |
| `total_files` | `int` | Total file count processed |
| `file_records` | `dict[str, FileRecord]` | Map of relative path → FileRecord |
| `tsa_servers_used` | `list[str]` | URLs of TSA servers successfully queried |
| `config_hash` | `str` (hex) | SHA-256 of the config.yml used for this run |

### FileRecord

Per-file data captured during a run.

| Field | Type | Description |
|-------|------|-------------|
| `relative_path` | `str` | Path relative to input directory |
| `file_size` | `int` | File size in bytes |
| `sha256` | `str` (hex) | SHA-256 hash |
| `md5` | `str` (hex) | MD5 hash |
| `modified_time` | `str` (ISO 8601) | Original file modification timestamp |
| `file_type` | `enum` | `video` / `image` / `document` / `other` |
| `metadata` | `VideoMetadata` / `ImageMetadata` / `DocumentMetadata` / `BasicMetadata` | File-type-specific metadata |
| `tsa_timestamps` | `list[TimestampSignature]` | TSA timestamps obtained (one per server) |
| `status` | `enum` | `processed` / `skipped_permission` / `skipped_locked` / `error` |
| `error_message` | `str` (optional) | Error details if status is error/skipped |

### VideoMetadata

| Field | Type | Description |
|-------|------|-------------|
| `duration_seconds` | `float` | Duration in seconds |
| `duration_hms` | `str` | Human-readable HH:MM:SS.ms |
| `frame_count` | `int` (optional) | Total frame count |
| `fps` | `float` | Frames per second |
| `bitrate_bps` | `int` (optional) | Overall bitrate in bits/second |
| `width` | `int` | Video width in pixels |
| `height` | `int` | Video height in pixels |
| `video_codec` | `str` | Video codec name (e.g., h264, hevc) |
| `audio_codec` | `str` (optional) | Audio codec name (e.g., aac, mp3) |
| `pixel_format` | `str` | Pixel format (e.g., yuv420p) |

### ImageMetadata

| Field | Type | Description |
|-------|------|-------------|
| `width` | `int` | Image width in pixels |
| `height` | `int` | Image height in pixels |
| `format` | `str` | Image format (e.g., jpeg, png) |
| `pixel_format` | `str` | Pixel format (e.g., rgb24, rgba) |
| `bits_per_channel` | `int` (optional) | Color depth per channel |
| `color_space` | `str` (optional) | Color space (e.g., sRGB, Display P3) |
| `exif` | `dict` (optional) | Extracted EXIF tags (camera, GPS, date, etc.) |

### DocumentMetadata

| Field | Type | Description |
|-------|------|-------------|
| `page_count` | `int` (optional) | Number of pages |
| `author` | `str` (optional) | Document author |
| `creator` | `str` (optional) | Creating application |
| `creation_date` | `str` (optional, ISO 8601) | Embedded creation date |
| `format` | `str` | Document format (pdf, docx, odt, txt) |

### BasicMetadata

Fallback when no file-type-specific extractor is available or `--skip-ffmpeg-meta` is passed.

| Field | Type | Description |
|-------|------|-------------|
| `mime_type` | `str` (optional) | Detected MIME type |
| `extension` | `str` | File extension (lowercase) |
| `notes` | `str` | e.g., "no specialized metadata available" |

### TimestampSignature

| Field | Type | Description |
|-------|------|-------------|
| `tsa_server_url` | `str` | URL of the TSA server |
| `tsa_server_label` | `str` | Human-readable name (e.g., "CATCert - Catalunya") |
| `signing_time` | `str` (ISO 8601) | Time from the TSA response |
| `token_hex` | `str` (hex) | Raw RFC 3161 TimeStampToken (DER-encoded, hex) |
| `serial_number` | `int` | TSA certificate serial number |
| `tsa_cert_subject` | `str` | TSA certificate subject DN |
| `tsa_cert_issuer` | `str` | TSA certificate issuer DN |
| `digest_algorithm` | `str` | OID of hash algorithm used (e.g., 2.16.840.1.101.3.4.2.1 for SHA-256) |
| `status` | `enum` | `success` / `timeout` / `rejected` / `error` |
| `error_message` | `str` (optional) | Error details if status is not success |

### DeltaChange

Represents a detected change on iterative runs. Stored in memory during the run; rendered into the delta report.

| Field | Type | Description |
|-------|------|-------------|
| `change_type` | `enum` | `added` / `removed` / `modified` / `metadata_changed` |
| `relative_path` | `str` | File path |
| `before_sha256` | `str` (optional) | Previous hash (for removed/modified) |
| `after_sha256` | `str` (optional) | Current hash (for added/modified) |
| `before_metadata` | `dict` (optional) | Previous metadata snapshot |
| `after_metadata` | `dict` (optional) | Current metadata snapshot |
| `before_tsa_timestamps` | `list[TimestampSignature]` (optional) | Original timestamps (carried forward) |

### TSAConfiguration

Parsed from `.signed_archive/config.yml`.

| Field | Type | Description |
|-------|------|-------------|
| `servers` | `list[TSAServer]` | Ordered list of TSA servers |
| `min_servers_required` | `int` | Minimum successful TSA queries per file (default: 1) |
| `request_timeout_seconds` | `int` | HTTP request timeout per server (default: 30) |
| `max_retries` | `int` | Max retry attempts per server (default: 3) |
| `retry_backoff_base_seconds` | `float` | Base for exponential backoff (default: 2.0) |
| `clock_skew_warning_threshold_seconds` | `float` | Warn if TSA timestamps differ by more than this (default: 5.0) |

### TSAServer

| Field | Type | Description |
|-------|------|-------------|
| `url` | `str` | TSA server URL (HTTP/HTTPS) |
| `label` | `str` | Human-readable label |
| `certificate_url` | `str` (optional) | URL to download TSA certificate for verification |
| `enabled` | `bool` | Whether this server is active (default: true) |

## State Transitions

### Run Lifecycle

```
[Start] → [Load Config] → [FFmpeg Check] → [Load Previous State]
  → [Walk Directory] → [Hash & Collect Metadata] → [Compare with Previous State]
    → [TSA Timestamp New/Changed Files] → [Build ZIP Archive]
      → [Compute Archive Hash] → [Sign Report (PAdES)] → [Sign Archive (CAdES)]
        → [Write State to .signed_archive/] → [Done]
```

### FileRecord Status Transitions

```
[Start] → processing → processed (success)
                    → skipped_permission (cannot read)
                    → skipped_locked (file locked)
                    → error (unexpected failure)
```

### TimestampSignature Status Transitions

```
[Start] → pending → success (TSA returned valid token)
                  → timeout (no response within timeout)
                  → rejected (TSA returned error status)
                  → error (network/protocol error)
```

## Validation Rules

1. **Config validation** (on load): All `servers[].url` must parse as valid HTTP/HTTPS URLs; `min_servers_required` must be >= 1 and <= len(enabled servers)
2. **State compatibility** (on load): `input_directory` must match the current run's input directory
3. **Hash consistency** (on comparison): A file is considered modified if SHA-256 differs; metadata-only change if SHA-256 matches but metadata fields differ
4. **Report completeness**: Every file with status `processed` must have at least `min_servers_required` successful TSA timestamps
