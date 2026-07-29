import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import portalocker
import typer

from signed_archive.config.defaults import DEFAULT_CONFIG
from signed_archive.config.loader import load_config, save_config
from signed_archive.models.config import TSAConfiguration
from signed_archive.models.report import ReportData
from signed_archive.models.run_state import (
    ChangeType,
    DeltaChange,
    FileRecord,
    FileStatus,
    RunState,
    TSAStatus,
    TimestampSignature,
)
from signed_archive.services.archiver import (
    compare_states,
    create_zip_archive,
    detect_config_hash_mismatch,
    load_previous_state,
    save_state,
)
from signed_archive.services.hasher import hash_file
from signed_archive.services.logger import get_run_logger, init_run_logger
from signed_archive.services.metadata import extract_metadata
from signed_archive.services.reporter import generate_delta_report, generate_report
from signed_archive.services.signer import load_certificate_and_key, sign_pdf, sign_zip_cades
from signed_archive.services.tsa import query_tsa_server
from signed_archive.utils.fs import check_ffprobe, walk_directory
from signed_archive.utils.locking import file_lock


def _generate_iso_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _compute_config_hash(config: TSAConfiguration) -> str:
    raw = json.dumps({"servers": [s.url for s in config.servers if s.enabled]}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _run_archive_pipeline(
    input_dir: Path,
    output_dir: Path,
    cert_path: Path | None = None,
    cert_key_path: Path | None = None,
    cert_password: str | None = None,
    tsa_config_path: Path | None = None,
    skip_ffmpeg_meta: bool = False,
    max_retries: int | None = None,
    timeout: int | None = None,
    no_sign: bool = False,
    dry_run: bool = False,
) -> int:
    logger = init_run_logger(output_dir)
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()

    signed_archive_dir = input_dir / ".signed_archive"
    lock_file = signed_archive_dir / ".lock"

    try:
        with file_lock(lock_file):
            if tsa_config_path is None:
                tsa_config_path = signed_archive_dir / "config.yml"

            if not tsa_config_path.exists():
                logger.info("No config found, generating default config")
                save_config(DEFAULT_CONFIG, tsa_config_path)

            try:
                config = load_config(tsa_config_path)
            except FileNotFoundError:
                typer.echo(f"Error: Config file not found: {tsa_config_path}", err=True)
                return 2
            except ValueError as e:
                typer.echo(f"Error: {e}", err=True)
                return 2

            if max_retries is not None:
                config.max_retries = max_retries
            if timeout is not None:
                config.request_timeout_seconds = timeout

            if not check_ffprobe() and not skip_ffmpeg_meta:
                typer.echo("Error: ffprobe not found. Install ffmpeg or use --skip-ffmpeg-meta", err=True)
                logger.error("ffprobe not found")
                return 2

            state_path = signed_archive_dir / "state.json"
            previous_state = load_previous_state(state_path)
            is_first_run = previous_state is None

            current_config_hash = _compute_config_hash(config)
            if previous_state and not is_first_run:
                detect_config_hash_mismatch(previous_state, current_config_hash)

            file_records: dict[str, FileRecord] = {}
            skipped = 0
            errors = 0

            all_files = list(walk_directory(input_dir))

            if not all_files:
                logger.info("No files found in directory")
                typer.echo("No files found to archive.")
                return 0

            for filepath in all_files:
                typer.echo(f"  Processing: {filepath.relative_to(input_dir)}")
                try:
                    rel_path = str(filepath.relative_to(input_dir)).replace("\\", "/")
                    sha256, md5 = hash_file(filepath)
                    file_size = filepath.stat().st_size
                    mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    file_type, metadata = extract_metadata(filepath, skip_ffmpeg=skip_ffmpeg_meta)

                    record = FileRecord(
                        relative_path=rel_path,
                        file_size=file_size,
                        sha256=sha256,
                        md5=md5,
                        modified_time=mtime,
                        file_type=file_type,
                        metadata=metadata,
                        status=FileStatus.PROCESSED,
                    )
                    file_records[rel_path] = record
                except PermissionError as e:
                    logger.warning(f"Permission denied: {filepath}")
                    rel_path = str(filepath.relative_to(input_dir)).replace("\\", "/")
                    file_records[rel_path] = FileRecord(
                        relative_path=rel_path,
                        file_size=0,
                        sha256="",
                        md5="",
                        modified_time="",
                        file_type="other",
                        status=FileStatus.SKIPPED_PERMISSION,
                        error_message=str(e),
                    )
                    skipped += 1
                except Exception as e:
                    logger.error(f"Error processing {filepath}: {e}")
                    rel_path = str(filepath.relative_to(input_dir)).replace("\\", "/")
                    file_records[rel_path] = FileRecord(
                        relative_path=rel_path,
                        file_size=0,
                        sha256="",
                        md5="",
                        modified_time="",
                        file_type="other",
                        status=FileStatus.ERROR,
                        error_message=str(e),
                    )
                    errors += 1

            if dry_run:
                typer.echo("\n" + "=" * 60)
                typer.echo("DRY RUN — Hashes and Metadata Only")
                typer.echo("=" * 60)
                for rel_path, record in file_records.items():
                    typer.echo(f"\n  {rel_path}")
                    typer.echo(f"    Type: {record.file_type}")
                    typer.echo(f"    Size: {record.file_size} bytes")
                    typer.echo(f"    SHA-256: {record.sha256}")
                    typer.echo(f"    MD5: {record.md5}")
                    typer.echo(f"    Status: {record.status.value}")
                typer.echo(f"\nTotal: {len(file_records)} files | Skipped: {skipped} | Errors: {errors}")
                return 0 if errors == 0 else 1

            changes: dict[str, DeltaChange] = {}
            if previous_state and not is_first_run:
                changes = compare_states(file_records, previous_state)

                if not changes:
                    typer.echo("No changes detected since last run.")
                    logger.info("No changes — skipping archive creation")
                    return 0

                typer.echo(f"Changes detected: {len(changes)} files changed")
                for path, change in changes.items():
                    logger.info(f"  {change.change_type.value.upper()}: {path}")

            ts = _generate_iso_timestamp()

            enabled_servers = [s for s in config.servers if s.enabled]
            tsa_servers_used: list[str] = []
            files_below_threshold: list[str] = []

            if not dry_run:
                for rel_path, record in file_records.items():
                    if record.status != FileStatus.PROCESSED:
                        continue

                    if record.sha256 in ("", None):
                        continue

                    timestamps: list[TimestampSignature] = []
                    with ThreadPoolExecutor(max_workers=len(enabled_servers)) as executor:
                        futures = {}
                        for server in enabled_servers:
                            future = executor.submit(
                                query_tsa_server, server.url, server.label, record.sha256, config
                            )
                            futures[future] = server

                        for future in as_completed(futures):
                            server = futures[future]
                            try:
                                ts_result = future.result()
                                timestamps.append(ts_result)
                                if ts_result.status == TSAStatus.SUCCESS:
                                    if server.url not in tsa_servers_used:
                                        tsa_servers_used.append(server.url)
                                    logger.info(f"TSA OK: {server.label} -> {ts_result.signing_time}")
                                else:
                                    logger.warning(f"TSA FAIL: {server.label} — {ts_result.error_message}")
                            except Exception as e:
                                logger.error(f"TSA ERROR: {server.label} — {e}")

                    record.tsa_timestamps = timestamps

                    success_timestamps = [t for t in timestamps if t.status == TSAStatus.SUCCESS and t.signing_time]
                    if len(success_timestamps) >= 2:
                        parsed_times = []
                        for ts_sig in success_timestamps:
                            try:
                                parsed_times.append(datetime.fromisoformat(ts_sig.signing_time))
                            except (ValueError, TypeError):
                                pass
                        if len(parsed_times) >= 2:
                            skew = (max(parsed_times) - min(parsed_times)).total_seconds()
                            if skew > config.clock_skew_warning_threshold_seconds:
                                logger.warning(
                                    "TSA clock skew detected for %s: %.1fs (threshold: %.1fs)",
                                    rel_path, skew, config.clock_skew_warning_threshold_seconds,
                                )

                    success_count = sum(1 for t in timestamps if t.status == TSAStatus.SUCCESS)

                    if success_count < config.min_servers_required:
                        files_below_threshold.append(rel_path)
                        logger.warning(f"TSA threshold not met for {rel_path}: {success_count}/{config.min_servers_required}")

            zip_path = output_dir / f"archive_{ts}.zip"
            logger.info(f"Creating archive: {zip_path}")

            try:
                create_zip_archive(input_dir, zip_path, file_records)
                logger.info(f"Archive created: {zip_path}")
            except Exception as e:
                logger.error(f"Failed to create archive: {e}")
                typer.echo(f"Error creating archive: {e}", err=True)
                return 2

            archive_sha256, archive_md5 = hash_file(zip_path)
            archive_size = zip_path.stat().st_size

            report_data = ReportData(
                run_id=str(hashlib.md5(str(datetime.now(timezone.utc)).encode()).hexdigest())[:8],
                run_timestamp=ts,
                input_directory=str(input_dir),
                is_first_run=is_first_run,
                archive_sha256=archive_sha256,
                archive_md5=archive_md5,
                archive_size=archive_size,
                total_files=len([r for r in file_records.values() if r.status == FileStatus.PROCESSED]),
                file_records=[r for r in file_records.values()],
                tsa_servers_used=tsa_servers_used,
                skipped_files=skipped,
                error_files=errors,
            )

            report_path = output_dir / f"report_{ts}.pdf"
            logger.info(f"Generating report: {report_path}")
            generate_report(report_data, report_path)

            if changes and previous_state:
                delta_path = output_dir / f"delta_{ts}.pdf"
                logger.info(f"Generating delta report: {delta_path}")
                generate_delta_report(
                    report_data,
                    list(changes.values()),
                    previous_state.run_id,
                    previous_state.run_timestamp,
                    delta_path,
                )

            if not no_sign and cert_path:
                cert_der, key_der = load_certificate_and_key(cert_path, cert_key_path, cert_password)
                sign_pdf(report_path, cert_der, key_der)
                logger.info(f"Report signed (PAdES): {report_path}")

                sig_path = output_dir / f"archive_{ts}.zip.sig"
                sign_zip_cades(zip_path, cert_der, key_der, sig_path)
                logger.info(f"Archive signed (CAdES): {sig_path}")

            run_state = RunState(
                run_id=report_data.run_id,
                run_timestamp=ts,
                input_directory=str(input_dir),
                archive_sha256=archive_sha256,
                archive_md5=archive_md5,
                archive_size=archive_size,
                total_files=report_data.total_files,
                file_records=file_records,
                tsa_servers_used=tsa_servers_used,
                config_hash=current_config_hash,
            )

            if previous_state and not is_first_run:
                for path, prev_record in previous_state.file_records.items():
                    if path not in file_records and path not in changes:
                        pass
                    if path in changes and changes[path].change_type == ChangeType.REMOVED:
                        pass
                for path, record in file_records.items():
                    if path in previous_state.file_records:
                        prev = previous_state.file_records[path]
                        if path not in changes:
                            record.tsa_timestamps = prev.tsa_timestamps

            save_state(run_state, state_path)
            logger.info(f"State saved: {state_path}")

            typer.echo(f"\nArchive: {zip_path}")
            typer.echo(f"Report: {report_path}")
            typer.echo(f"Total files: {report_data.total_files}")

            if files_below_threshold:
                typer.echo(f"Warning: {len(files_below_threshold)} files below TSA threshold", err=True)

            if errors > 0 or files_below_threshold:
                return 1
            return 0
    except portalocker.exceptions.LockException:
        typer.echo("Error: Could not acquire file lock. Another process may be running.", err=True)
        return 2
