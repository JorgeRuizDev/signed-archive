# signed-archive

CLI tool for RFC 3161 TSA timestamping, ZIP archiving, and eIDAS-compliant PDF/A-3 reporting. Targets legal validity in Spain using qualified TSA providers.

## Install

```bash
uv tool install signed-archive --from git+https://github.com/JorgeRuizDev/signed-archive.git
```

## Quickstart

### Create an archive

```bash
signed-archive archive -i ./my_files -o ./output --skip-ffmpeg-meta
```

Produces `archive_<TS>.zip`, `report_<TS>.pdf`, `report_<TS>.json`, `run_<TS>.log`, and `.signed_archive/state.json`.

### Sign with a certificate

```bash
signed-archive archive -i ./my_files -o ./output --cert cert.p12 --cert-password "pass"
```

Produces CAdES detached signatures (`archive_<TS>.zip.sig`). The JSON report is the authoritative integrity record.

### Iterative update

Run again on the same directory. Added/removed/modified files are detected via hash comparison, generating `delta_<TS>.pdf` and `delta_<TS>.json` change reports. Unchanged files retain their original timestamps.

### Manage TSA servers

```bash
signed-archive config show -i ./my_files
signed-archive config add http://tsa.example.com "Custom TSA" -i ./my_files
signed-archive config remove "Custom TSA" -i ./my_files
signed-archive config init -i ./my_files --force
```

### Verify an archive

```bash
signed-archive verify -a archive_<TS>.zip -r report_<TS>.pdf
```

## Default TSA servers

| Server | URL |
|--------|-----|
| ACCV — Comunidad Valenciana (ISTEC) | `http://tss.accv.es:8318/tsa` |
| FreeTSA | `https://freetsa.org/tsr` |
| DigiCert | `http://timestamp.digicert.com` |
| Sectigo | `http://timestamp.sectigo.com` |

Run `signed-archive config show` to view the current configuration. Use `signed-archive config init --force` to reset to defaults.

## Environment variables

| Variable | Equivalent |
|----------|-----------|
| `SIGNED_ARCHIVE_CERT` | `--cert` |
| `SIGNED_ARCHIVE_CERT_KEY` | `--cert-key` |
| `SIGNED_ARCHIVE_CERT_PASSWORD` | `--cert-password` |
| `SIGNED_ARCHIVE_TSA_CONFIG` | `--tsa-config` |
| `SIGNED_ARCHIVE_SKIP_FFMPEG` | `--skip-ffmpeg-meta` |

CLI flags override environment variables.

## Requirements

- Python >= 3.11
- `ffprobe` (for video/image metadata extraction; optional with `--skip-ffmpeg-meta`)
