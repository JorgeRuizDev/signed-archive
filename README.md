# signed-archive

CLI tool for RFC 3161 TSA timestamping, ZIP archiving, and eIDAS-compliant PDF/A-3 reporting. Targets legal validity in Spain using qualified TSA providers (ACCV, CATCert, IZENPE).

## Install

```bash
git clone https://github.com/JorgeRuizDev/signed-archive.git
cd signed-archive
uv sync
```

## Quickstart

### First-time archive

```bash
uv run signed-archive archive -i ./my_files -o ./output --skip-ffmpeg-meta --no-sign
```

Produces:
- `archive_<TS>.zip` — timestamped ZIP of the directory
- `report_<TS>.pdf` — per-file SHA-256, MD5, metadata, TSA timestamps
- `run_<TS>.log` — execution log
- `.signed_archive/state.json` — run state for iterative change detection

### Signed archive with a certificate

```bash
uv run signed-archive archive -i ./my_files -o ./output --cert cert.p12 --cert-password "pass"
```

### Iterative update

Run again on the same directory. The tool detects added/removed/modified files via hash comparison against `.signed_archive/state.json` and generates a `delta_<TS>.pdf` change report. Unchanged files retain their original timestamps.

### Manage TSA servers

```bash
uv run signed-archive config show -i ./my_files
uv run signed-archive config add http://tsa.example.com "Custom TSA" -i ./my_files
uv run signed-archive config remove "Custom TSA" -i ./my_files
uv run signed-archive config init -i ./my_files --force
```

### Verify an archive

```bash
uv run signed-archive verify -a archive_<TS>.zip -r report_<TS>.pdf
```

### Environment variables

| Variable | Equivalent |
|----------|-----------|
| `SIGNED_ARCHIVE_CERT` | `--cert` |
| `SIGNED_ARCHIVE_CERT_KEY` | `--cert-key` |
| `SIGNED_ARCHIVE_CERT_PASSWORD` | `--cert-password` |
| `SIGNED_ARCHIVE_TSA_CONFIG` | `--tsa-config` |
| `SIGNED_ARCHIVE_SKIP_FFMPEG` | `--skip-ffmpeg-meta` |

CLI flags override environment variables.
