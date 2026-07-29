# CLI Contract: TSA Sign & Archive

## Command: `signed-archive`

Top-level entry point. Displays help if no subcommand given.

```
Usage: signed-archive [OPTIONS] COMMAND [ARGS]...

Options:
  --version   Show the version and exit.
  --help      Show this message and exit.

Commands:
  archive   Run the archive and timestamp process
  verify    Verify an existing archive and report
  config    Manage TSA configuration
```

---

## Subcommand: `archive`

Run the archiving process: hash files, query TSA servers, create ZIP, generate signed reports.

```
Usage: signed-archive archive [OPTIONS]

Options:
  -i, --input DIRECTORY           Directory to archive (required)
  -o, --output DIRECTORY          Output directory for archive and reports
                                  (default: current working directory)
  -c, --cert FILE                 X.509 certificate file (PEM or P12/PFX)
                                  for signing report and archive (required
                                  for signing)
  -k, --cert-key FILE             Private key file (PEM). Required if --cert
                                  is PEM; ignored if --cert is P12/PFX
  -p, --cert-password TEXT        Password for P12/PFX certificate or
                                  encrypted private key
      --tsa-config FILE           Path to TSA config YAML file
                                  (default: .signed_archive/config.yml
                                  inside --input directory)
      --skip-ffmpeg-meta          Skip ffmpeg metadata extraction. Use if
                                  ffmpeg is not installed. Basic metadata
                                  (size, hashes) only.
      --max-retries INTEGER       Max TSA request retries per server
                                  (default: 3)
      --timeout INTEGER           TSA request timeout in seconds
                                  (default: 30)
      --no-sign                   Skip digital signing of report and archive.
                                  Report still generated as unsigned PDF/A-3.
      --dry-run                   Compute hashes and metadata but do NOT
                                  query TSA servers, create archive, or
                                  generate reports. Useful for preview.
      --help                      Show this message and exit.

Exit Codes:
  0   Success (all files processed, archive created, report signed)
  1   Partial success (some files skipped or some TSA servers failed,
      but archive and report were generated)
  2   Error (configuration error, ffmpeg not found without --skip-ffmpeg-meta,
      input directory does not exist, etc.)
```

### Archive Output Files

All output files use ISO 8601 UTC timestamps in their names.

| File Pattern | Description |
|-------------|-------------|
| `archive_<TS>.zip` | ZIP archive of input directory |
| `archive_<TS>.zip.sig` | Detached CAdES signature for the ZIP |
| `report_<TS>.pdf` | Signed PDF/A-3 archive report |
| `delta_<TS>.pdf` | Delta change report (iterative runs only; omitted if no changes or first run) |
| `run_<TS>.log` | Run execution log |

Where `<TS>` = `YYYYMMDDTHHMMSSZ` (e.g., `20260729T203000Z`).

---

## Subcommand: `verify`

Verify the integrity and authenticity of a previously created archive and report.

```
Usage: signed-archive verify [OPTIONS]

Options:
  -a, --archive FILE             Path to the ZIP archive (required)
  -r, --report FILE              Path to the signed report PDF (required)
      --verify-tsa-certs         Also verify TSA certificates against the
                                 EU Trusted List (EUTL). Requires network.
      --output FILE              Write verification report to file
                                 (default: stdout)
      --format [text|json]       Output format (default: text)
      --help                     Show this message and exit.

Exit Codes:
  0   All checks passed (hashes match, signatures valid, timestamps verifiable)
  1   Verification failures found (hash mismatches, invalid signatures, etc.)
  2   Error (files not found, unreadable, etc.)
```

### Verify Output (text format)

```
VERIFICATION REPORT
===================
Archive:  archive_20260729T203000Z.zip
Report:   report_20260729T203000Z.pdf

Archive Hash Check .................. PASS
  SHA-256 matches report record

Report Signature Check .............. PASS
  Signer: CN=Jorge, O=Example, C=ES
  Signed at: 2026-07-29T20:30:00Z

File Integrity Check ................ PASS
  Files checked: 10 | Matched: 10 | Mismatched: 0

  file_record     [PASS] a0b1c2d3...
  document.pdf    [PASS] e4f5g6h7...
  video.mp4       [PASS] i8j9k0l1...

TSA Timestamp Check ................. PASS
  Total timestamps checked: 30 | Valid: 30 | Invalid: 0

  ACCV (Comunidad Valenciana):   10/10 valid
  CATCert (Catalunya):           10/10 valid
  IZENPE (País Vasco):           10/10 valid

OVERALL: PASS
```

### Verify Output (json format)

```json
{
  "overall": "PASS",
  "archive": {
    "path": "archive_20260729T203000Z.zip",
    "sha256": "a0b1c2d3e4f5...",
    "md5": "1a2b3c4d5e6f...",
    "checks": { "hash_matches_report": true }
  },
  "report": {
    "path": "report_20260729T203000Z.pdf",
    "signature_valid": true,
    "signer": "CN=Jorge, O=Example, C=ES",
    "signed_at": "2026-07-29T20:30:00Z"
  },
  "files": {
    "total": 10,
    "matched": 10,
    "mismatched": 0,
    "details": [
      {
        "path": "video.mp4",
        "status": "PASS",
        "sha256_report": "i8j9k0l1...",
        "sha256_archive": "i8j9k0l1..."
      }
    ]
  },
  "tsa_timestamps": {
    "total": 30,
    "valid": 30,
    "invalid": 0,
    "by_server": {
      "ACCV - Comunidad Valenciana": { "total": 10, "valid": 10 },
      "CATCert - Catalunya": { "total": 10, "valid": 10 },
      "IZENPE - País Vasco": { "total": 10, "valid": 10 }
    }
  }
}
```

---

## Subcommand: `config`

Manage TSA configuration stored in `.signed_archive/config.yml`.

```
Usage: signed-archive config COMMAND [ARGS]...

Commands:
  init     Initialize or reset default TSA configuration
  show     Show current TSA configuration
  add      Add a TSA server to the configuration
  remove   Remove a TSA server by URL or label
```

### `config init`

Creates or overwrites `.signed_archive/config.yml` in the target directory with the default 3 Spanish TSA providers.

```
Usage: signed-archive config init [OPTIONS]

Options:
  -i, --input DIRECTORY    Directory containing .signed_archive/ folder
                           (default: current working directory)
      --force              Overwrite existing config without confirmation
      --help               Show this message and exit.
```

### `config show`

Displays the current configuration.

```
Usage: signed-archive config show [OPTIONS]

Options:
  -i, --input DIRECTORY    Directory containing .signed_archive/ folder
                           (default: current working directory)
      --help               Show this message and exit.
```

### `config add`

Adds a new TSA server.

```
Usage: signed-archive config add [OPTIONS] URL LABEL

Options:
  -i, --input DIRECTORY        Directory containing .signed_archive/ folder
                               (default: current working directory)
      --certificate-url TEXT   URL to download the TSA certificate
      --help                   Show this message and exit.

Arguments:
  URL     TSA server URL (e.g., http://tsa.example.com)
  LABEL   Human-readable label (e.g., "My TSA Provider")
```

### `config remove`

Removes a TSA server by URL or label.

```
Usage: signed-archive config remove [OPTIONS] IDENTIFIER

Options:
  -i, --input DIRECTORY    Directory containing .signed_archive/ folder
                           (default: current working directory)
      --help               Show this message and exit.

Arguments:
  IDENTIFIER   TSA server URL or label to remove
```

---

## Default Configuration (`config.yml`)

The default configuration generated by `config init`:

```yaml
# TSA Sign & Archive Configuration
# Generated by signed-archive config init

tsa:
  min_servers_required: 1
  request_timeout_seconds: 30
  max_retries: 3
  retry_backoff_base_seconds: 2.0
  clock_skew_warning_threshold_seconds: 5.0

  servers:
    - url: http://tss.accv.es:8318/tsa
      label: ACCV - Comunidad Valenciana (ISTEC)
      certificate_url: https://www.accv.es/fileadmin/Archivos/certificados/tsa1accv2016.cer
      enabled: true

    - url: http://psis.catcert.net/psis/catcert/tsp
      label: CATCert - Catalunya
      certificate_url: ~
      enabled: true

    - url: http://tsa.izenpe.com
      label: IZENPE - País Vasco
      certificate_url: ~
      enabled: true
```

---

## Environment Variables

As an alternative to CLI flags, the following environment variables are supported:

| Variable | Equivalent Flag | Description |
|----------|----------------|-------------|
| `SIGNED_ARCHIVE_CERT` | `--cert` | Path to X.509 certificate file |
| `SIGNED_ARCHIVE_CERT_KEY` | `--cert-key` | Path to private key file |
| `SIGNED_ARCHIVE_CERT_PASSWORD` | `--cert-password` | Certificate/key password |
| `SIGNED_ARCHIVE_TSA_CONFIG` | `--tsa-config` | Path to TSA config YAML |
| `SIGNED_ARCHIVE_SKIP_FFMPEG` | `--skip-ffmpeg-meta` | Set to "1" or "true" to skip ffmpeg |

CLI flags take precedence over environment variables.
