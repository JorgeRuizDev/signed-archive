import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from signed_archive.models.run_state import (
    ChangeType,
    DeltaChange,
    FileRecord,
    FileStatus,
    RunState,
    TimestampSignature,
    TSAStatus,
)


def create_zip_archive(
    input_dir: Path,
    output_path: Path,
    file_records: dict[str, FileRecord],
    previous_state: RunState | None = None,
    changed_files: dict[str, DeltaChange] | None = None,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for rel_path, record in file_records.items():
            if record.status != FileStatus.PROCESSED:
                continue
            _write_file_to_zip(zf, input_dir, rel_path)

    return output_path.stat().st_size


def update_zip_archive(
    input_dir: Path,
    output_path: Path,
    file_records: dict[str, FileRecord],
    changes: dict[str, DeltaChange],
    previous_state: RunState,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    modified_paths = {
        path
        for path, change in changes.items()
        if change.change_type in (ChangeType.MODIFIED, ChangeType.METADATA_CHANGED)
    }
    added_paths = {
        path for path, change in changes.items() if change.change_type == ChangeType.ADDED
    }

    if not output_path.exists():
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            for rel_path, record in file_records.items():
                if record.status != FileStatus.PROCESSED:
                    continue
                _write_file_to_zip(zf, input_dir, rel_path)
    else:
        fd, temp_path_str = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        temp_path = Path(temp_path_str)
        try:
            with zipfile.ZipFile(output_path, "r") as old_zf, zipfile.ZipFile(
                temp_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True
            ) as new_zf:
                for entry in old_zf.infolist():
                    if entry.filename in modified_paths or entry.is_dir():
                        continue
                    new_zf.writestr(entry, old_zf.read(entry.filename))

                for rel_path, record in file_records.items():
                    if record.status != FileStatus.PROCESSED:
                        continue
                    if rel_path in modified_paths or rel_path in added_paths:
                        _write_file_to_zip(new_zf, input_dir, rel_path)

            shutil.move(temp_path, output_path)
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    return output_path.stat().st_size


def load_previous_state(state_path: Path) -> RunState | None:
    if not state_path.exists():
        return None

    try:
        with open(state_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.getLogger("signed_archive").warning("Failed to load previous state from %s: %s", state_path, e)
        return None

    run_state = RunState()
    run_state.run_id = raw.get("run_id", "")
    run_state.run_timestamp = raw.get("run_timestamp", "")
    run_state.input_directory = raw.get("input_directory", "")
    run_state.archive_sha256 = raw.get("archive_sha256", "")
    run_state.archive_md5 = raw.get("archive_md5", "")
    run_state.archive_size = raw.get("archive_size", 0)
    run_state.total_files = raw.get("total_files", 0)
    run_state.tsa_servers_used = raw.get("tsa_servers_used", [])
    run_state.config_hash = raw.get("config_hash", "")

    for path, fr_data in raw.get("file_records", {}).items():
        tsa_timestamps: list[TimestampSignature] = []
        for ts_data in fr_data.get("tsa_timestamps", []):
            tsa_timestamps.append(TimestampSignature(
                tsa_server_url=ts_data.get("tsa_server_url", ""),
                tsa_server_label=ts_data.get("tsa_server_label", ""),
                signing_time=ts_data.get("signing_time", ""),
                token_hex=ts_data.get("token_hex", ""),
                serial_number=ts_data.get("serial_number", 0),
                tsa_cert_subject=ts_data.get("tsa_cert_subject", ""),
                tsa_cert_issuer=ts_data.get("tsa_cert_issuer", ""),
                digest_algorithm=ts_data.get("digest_algorithm", ""),
                status=TSAStatus(ts_data.get("status", "success")),
                error_message=ts_data.get("error_message"),
            ))

        record = FileRecord(
            relative_path=fr_data.get("relative_path", path),
            file_size=fr_data.get("file_size", 0),
            sha256=fr_data.get("sha256", ""),
            md5=fr_data.get("md5", ""),
            modified_time=fr_data.get("modified_time", ""),
            file_type=fr_data.get("file_type", "other"),
            tsa_timestamps=tsa_timestamps,
            status=FileStatus(fr_data.get("status", "processed")),
            error_message=fr_data.get("error_message"),
        )
        run_state.file_records[path] = record

    return run_state


def save_state(state: RunState, state_path: Path) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "run_id": state.run_id,
        "run_timestamp": state.run_timestamp,
        "input_directory": state.input_directory,
        "archive_sha256": state.archive_sha256,
        "archive_md5": state.archive_md5,
        "archive_size": state.archive_size,
        "total_files": state.total_files,
        "file_records": {},
        "tsa_servers_used": state.tsa_servers_used,
        "config_hash": state.config_hash,
    }

    for path, record in state.file_records.items():
        data["file_records"][path] = {
            "relative_path": record.relative_path,
            "file_size": record.file_size,
            "sha256": record.sha256,
            "md5": record.md5,
            "modified_time": record.modified_time,
            "file_type": record.file_type,
            "status": record.status.value,
            "error_message": record.error_message,
            "tsa_timestamps": [
                {
                    "tsa_server_url": ts.tsa_server_url,
                    "tsa_server_label": ts.tsa_server_label,
                    "signing_time": ts.signing_time,
                    "token_hex": ts.token_hex,
                    "serial_number": ts.serial_number,
                    "tsa_cert_subject": ts.tsa_cert_subject,
                    "tsa_cert_issuer": ts.tsa_cert_issuer,
                    "digest_algorithm": ts.digest_algorithm,
                    "status": ts.status.value,
                    "error_message": ts.error_message,
                }
                for ts in record.tsa_timestamps
            ],
        }

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def compare_states(
    current_records: dict[str, FileRecord],
    previous_state: RunState,
) -> dict[str, DeltaChange]:
    changes: dict[str, DeltaChange] = {}

    for path, record in current_records.items():
        if path not in previous_state.file_records:
            changes[path] = DeltaChange(
                change_type=ChangeType.ADDED,
                relative_path=path,
                after_sha256=record.sha256,
                after_metadata=_record_metadata_dict(record),
            )
        else:
            prev = previous_state.file_records[path]
            if record.sha256 != prev.sha256:
                changes[path] = DeltaChange(
                    change_type=ChangeType.MODIFIED,
                    relative_path=path,
                    before_sha256=prev.sha256,
                    after_sha256=record.sha256,
                    before_metadata=_record_metadata_dict(prev),
                    after_metadata=_record_metadata_dict(record),
                    before_tsa_timestamps=prev.tsa_timestamps,
                )
            elif _record_metadata_dict(record) != _record_metadata_dict(prev):
                changes[path] = DeltaChange(
                    change_type=ChangeType.METADATA_CHANGED,
                    relative_path=path,
                    before_sha256=prev.sha256,
                    after_sha256=record.sha256,
                    before_metadata=_record_metadata_dict(prev),
                    after_metadata=_record_metadata_dict(record),
                    before_tsa_timestamps=prev.tsa_timestamps,
                )
            else:
                record.tsa_timestamps = prev.tsa_timestamps

    for path, prev_record in previous_state.file_records.items():
        if path not in current_records:
            changes[path] = DeltaChange(
                change_type=ChangeType.REMOVED,
                relative_path=path,
                before_sha256=prev_record.sha256,
                before_metadata=_record_metadata_dict(prev_record),
                before_tsa_timestamps=prev_record.tsa_timestamps,
            )

    return changes


def _write_file_to_zip(zf: zipfile.ZipFile, input_dir: Path, rel_path: str) -> None:
    file_path = input_dir / rel_path
    if not file_path.exists():
        return
    zf.write(file_path, rel_path)
    info = zf.getinfo(rel_path)
    mtime = file_path.stat().st_mtime
    info.date_time = datetime.fromtimestamp(mtime, tz=timezone.utc).timetuple()[:6]


def _record_metadata_dict(record: FileRecord) -> dict:
    return {
        "file_type": record.file_type,
        "file_size": record.file_size,
    }


def detect_config_hash_mismatch(previous_state: RunState, current_config_hash: str) -> None:
    if not previous_state.config_hash:
        return
    if previous_state.config_hash != current_config_hash:
        logging.getLogger("signed_archive").warning(
            "TSA configuration hash mismatch: config has changed since previous run"
        )
