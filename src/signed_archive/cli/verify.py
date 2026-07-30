import json
from pathlib import Path
from typing import Optional

import typer

from signed_archive.services.hasher import hash_file
from signed_archive.services.verifier import (
    VerificationReport,
    verify_archive_integrity,
)


def verify_command(
    archive: Path = typer.Option(
        ..., "--archive", "-a", help="Path to the ZIP archive", exists=True, readable=True
    ),
    report: Path = typer.Option(
        ..., "--report", "-r", help="Path to the report PDF", exists=True, readable=True
    ),
    verify_tsa_certs: bool = typer.Option(
        False, "--verify-tsa-certs", help="Also verify TSA certificates against EUTL"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", help="Write verification report to file"
    ),
    format: str = typer.Option(
        "text", "--format", help="Output format: text or json"
    ),
) -> int:
    result = verify_archive_integrity(archive, report)

    if format == "json":
        output_text = _format_json(result)
    else:
        output_text = _format_text(result)

    if output:
        output.write_text(output_text, encoding="utf-8")
        typer.echo(f"Verification report written to: {output}")
    else:
        typer.echo(output_text)

    return _exit_code_from_result(result)


def _exit_code_from_result(result: VerificationReport) -> int:
    if result.overall == "PASS":
        return 0
    if result.overall == "FAIL":
        return 1
    return 2


def _format_text(result: VerificationReport) -> str:
    lines = [
        "VERIFICATION REPORT",
        "===================",
        f"Archive:  {result.archive_path}",
        f"Report:   {result.report_path}",
        "",
    ]

    ah_status = "PASS" if result.archive_hash_check else "FAIL"
    lines.append(f"Archive Hash Check .................. {ah_status}")

    fi_status = "PASS" if result.files_total > 0 and result.files_mismatched == 0 else "FAIL"
    lines.append(f"File Integrity Check ................ {fi_status}")
    lines.append(f"  Files checked: {result.files_total} | Matched: {result.files_matched} | Mismatched: {result.files_mismatched}")
    lines.append("")
    for detail in result.file_details:
        status = "PASS" if detail["status"] == "PASS" else "FAIL"
        lines.append(f"  {detail['path']:40s} [{status}] {detail.get('sha256_report', '')[:16]}...")

    ts_status = "PASS" if result.tsa_total > 0 and result.tsa_invalid == 0 else "FAIL"
    lines.append("")
    lines.append(f"TSA Timestamp Check ................. {ts_status}")
    lines.append(f"  Total timestamps checked: {result.tsa_total} | Valid: {result.tsa_valid} | Invalid: {result.tsa_invalid}")

    lines.append("")
    lines.append(f"OVERALL: {result.overall}")
    return "\n".join(lines)


def _format_json(result: VerificationReport) -> str:
    return json.dumps({
        "overall": result.overall,
        "archive": {
            "path": str(result.archive_path),
            "checks": {"hash_matches_report": result.archive_hash_check},
        },
        "files": {
            "total": result.files_total,
            "matched": result.files_matched,
            "mismatched": result.files_mismatched,
            "details": result.file_details,
        },
        "tsa_timestamps": {
            "total": result.tsa_total,
            "valid": result.tsa_valid,
            "invalid": result.tsa_invalid,
        },
    }, indent=2)
