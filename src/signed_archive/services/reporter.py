import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF

from signed_archive.models.report import ReportData
from signed_archive.models.run_state import ChangeType, DeltaChange, FileRecord, TimestampSignature


class PDFReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, "TSA Sign & Archive Report", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_report(report_data: ReportData, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = PDFReport()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Archive Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Run ID: {report_data.run_id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Timestamp: {report_data.run_timestamp}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Input Directory: {report_data.input_directory}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Total Files: {report_data.total_files}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Archive SHA-256: {report_data.archive_sha256}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Archive MD5: {report_data.archive_md5}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Archive Size: {report_data.archive_size} bytes", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    if report_data.tsa_servers_used:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "TSA Servers Used:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for srv in report_data.tsa_servers_used:
            pdf.cell(0, 5, f"  - {srv}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    render_file_records(pdf, report_data.file_records)

    if report_data.skipped_files > 0 or report_data.error_files > 0:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, f"Skipped: {report_data.skipped_files} | Errors: {report_data.error_files}", new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(output_path))
    return output_path


def render_file_records(pdf: FPDF, records: list[FileRecord]):
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, "File Records", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    for i, record in enumerate(records):
        if pdf.get_y() > pdf.h - 60:
            pdf.add_page()

        pdf.set_fill_color(240, 240, 240) if i % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        y_start = pdf.get_y()

        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, record.relative_path, fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 7)
        pdf.cell(0, 4, f"SHA-256: {record.sha256}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 4, f"MD5: {record.md5} | Type: {record.file_type} | Size: {record.file_size} bytes", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 4, f"Modified: {record.modified_time}", new_x="LMARGIN", new_y="NEXT")

        if record.tsa_timestamps:
            pdf.cell(0, 4, "TSA Timestamps:", new_x="LMARGIN", new_y="NEXT")
            for ts in record.tsa_timestamps:
                pdf.set_font("Helvetica", "", 6)
                status_mark = "OK" if ts.status.value == "success" else ts.status.value.upper()
                pdf.cell(0, 3, f"  [{status_mark}] {ts.tsa_server_label}: {ts.signing_time}", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 7)

        metadata = record.metadata
        if hasattr(metadata, "duration_seconds") and metadata.duration_seconds:
            pdf.cell(0, 4, f"  Duration: {metadata.duration_hms} | FPS: {metadata.fps:.2f} | {metadata.width}x{metadata.height} | Codec: {metadata.video_codec}", new_x="LMARGIN", new_y="NEXT")
        elif hasattr(metadata, "format") and metadata.format:
            pdf.cell(0, 4, f"  Format: {metadata.format} | {metadata.width}x{metadata.height} | {metadata.pixel_format}", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(2)


def generate_delta_report(
    report_data: ReportData,
    changes: list[DeltaChange],
    previous_run_id: str,
    previous_run_timestamp: str,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = PDFReport()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Delta Change Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Current Run: {report_data.run_timestamp} ({report_data.run_id})", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Previous Run: {previous_run_timestamp} ({previous_run_id})", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    added = [c for c in changes if c.change_type == ChangeType.ADDED]
    removed = [c for c in changes if c.change_type == ChangeType.REMOVED]
    modified = [c for c in changes if c.change_type == ChangeType.MODIFIED]
    meta_only = [c for c in changes if c.change_type == ChangeType.METADATA_CHANGED]

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, f"Summary: {len(added)} added, {len(removed)} removed, {len(modified)} modified, {len(meta_only)} metadata-only changes", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    if added:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "ADDED FILES", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        for c in added:
            pdf.cell(0, 5, f"  + {c.relative_path}  SHA-256: {c.after_sha256}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    if removed:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "REMOVED FILES", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        for c in removed:
            pdf.cell(0, 5, f"  - {c.relative_path}  SHA-256: {c.before_sha256 if c.before_sha256 else 'N/A'}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    if modified:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "MODIFIED FILES", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        for c in modified:
            pdf.cell(0, 5, f"  ~ {c.relative_path}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, f"      Before: {c.before_sha256 if c.before_sha256 else 'N/A'}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, f"      After:  {c.after_sha256 if c.after_sha256 else 'N/A'}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    if meta_only:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "METADATA-ONLY CHANGES", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        for c in meta_only:
            pdf.cell(0, 5, f"  * {c.relative_path} (hash unchanged)", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    pdf.output(str(output_path))
    return output_path


def _file_record_to_dict(record: FileRecord) -> dict:
    metadata_dict = asdict(record.metadata) if record.metadata else None
    return {
        "relative_path": record.relative_path,
        "file_size": record.file_size,
        "sha256": record.sha256,
        "md5": record.md5,
        "modified_time": record.modified_time,
        "file_type": record.file_type,
        "status": record.status.value if hasattr(record.status, "value") else str(record.status),
        "metadata": metadata_dict,
        "tsa_timestamps": [asdict(ts) for ts in record.tsa_timestamps] if record.tsa_timestamps else [],
        "error_message": record.error_message,
    }


def _delta_change_to_dict(change: DeltaChange) -> dict:
    result = {
        "change_type": change.change_type.value if hasattr(change.change_type, "value") else str(change.change_type),
        "relative_path": change.relative_path,
    }
    if change.before_sha256 is not None:
        result["before_sha256"] = change.before_sha256
    if change.after_sha256 is not None:
        result["after_sha256"] = change.after_sha256
    if change.before_metadata is not None:
        result["before_metadata"] = change.before_metadata
    if change.after_metadata is not None:
        result["after_metadata"] = change.after_metadata
    return result


def generate_json_report(report_data: ReportData, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "run_id": report_data.run_id,
        "run_timestamp": report_data.run_timestamp,
        "input_directory": report_data.input_directory,
        "is_first_run": report_data.is_first_run,
        "archive_sha256": report_data.archive_sha256,
        "archive_md5": report_data.archive_md5,
        "archive_size": report_data.archive_size,
        "total_files": report_data.total_files,
        "skipped_files": report_data.skipped_files,
        "error_files": report_data.error_files,
        "tsa_servers_used": report_data.tsa_servers_used,
        "file_records": [_file_record_to_dict(r) for r in report_data.file_records],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return output_path


def generate_json_delta(
    report_data: ReportData,
    changes: list[DeltaChange],
    previous_run_id: str,
    previous_run_timestamp: str,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    added = sum(1 for c in changes if c.change_type == ChangeType.ADDED)
    removed = sum(1 for c in changes if c.change_type == ChangeType.REMOVED)
    modified = sum(1 for c in changes if c.change_type == ChangeType.MODIFIED)
    metadata_changed = sum(1 for c in changes if c.change_type == ChangeType.METADATA_CHANGED)

    data = {
        "current_run": {
            "run_id": report_data.run_id,
            "run_timestamp": report_data.run_timestamp,
        },
        "previous_run": {
            "run_id": previous_run_id,
            "run_timestamp": previous_run_timestamp,
        },
        "summary": {
            "added": added,
            "removed": removed,
            "modified": modified,
            "metadata_changed": metadata_changed,
        },
        "changes": [_delta_change_to_dict(c) for c in changes],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return output_path
