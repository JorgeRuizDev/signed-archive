import hashlib
import re
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from zipfile import ZipFile

from signed_archive.services.hasher import hash_file
from signed_archive.services.tsa import verify_tsa_timestamp


@dataclass
class VerificationReport:
    overall: str = "PASS"
    archive_path: str = ""
    report_path: str = ""
    archive_hash_check: bool = True
    files_total: int = 0
    files_matched: int = 0
    files_mismatched: int = 0
    file_details: list[dict] = field(default_factory=list)
    tsa_total: int = 0
    tsa_valid: int = 0
    tsa_invalid: int = 0


BUFFER_SIZE = 8 * 1024 * 1024


def verify_archive_integrity(archive_path: Path, report_path: Path) -> VerificationReport:
    result = VerificationReport(
        archive_path=str(archive_path),
        report_path=str(report_path),
    )

    report_text = _extract_pdf_text(report_path)

    expected_hashes = _parse_file_hashes_from_report(report_text)
    expected_archive_hash = _parse_archive_hash_from_report(report_text)

    archive_sha256, _ = hash_file(archive_path)
    if expected_archive_hash:
        result.archive_hash_check = archive_sha256.startswith(expected_archive_hash)
    else:
        result.archive_hash_check = True

    tsa_entries = _parse_tsa_entries_from_report(report_text)
    _check_file_hashes(result, archive_path, expected_hashes, tsa_entries)

    _check_tsa_timestamps(result, archive_path, expected_hashes, tsa_entries)

    result.overall = _determine_overall(result)

    return result


def _extract_pdf_text(pdf_path: Path) -> str:
    data = pdf_path.read_bytes()
    text_parts = []

    stream_re = re.compile(rb'stream\r?\n(.*?)\r?\nendstream', re.DOTALL)
    for match in stream_re.finditer(data):
        stream_body = match.group(1).rstrip(b'\r\n\t ')
        try:
            decompressed = zlib.decompress(stream_body)
            text_parts.append(decompressed.decode('latin-1', errors='ignore'))
        except Exception:
            text_parts.append(stream_body.decode('latin-1', errors='ignore'))

    raw = '\n'.join(text_parts)
    return _extract_text_from_content(raw)


def _extract_text_from_content(content: str) -> str:
    result_parts = []

    bt_re = re.compile(r'BT(.*?)ET', re.DOTALL)
    for match in bt_re.finditer(content):
        block = match.group(1)

        tj_re = re.compile(r'\[(.*?)\]\s*TJ', re.DOTALL)
        for tjm in tj_re.finditer(block):
            for piece in re.finditer(r'\(((?:[^()]|\([^)]*\))*)\)', tjm.group(1)):
                result_parts.append(piece.group(1))

        block_stripped = re.sub(r'\[.*?\]\s*TJ', '', block, flags=re.DOTALL)
        for tjm in re.finditer(r'\(((?:[^()]|\([^)]*\))*)\)\s*Tj', block_stripped):
            result_parts.append(tjm.group(1))

    return '\n'.join(result_parts)


def _parse_file_hashes_from_report(report_text: str) -> dict[str, str]:
    expected: dict[str, str] = {}
    if not report_text:
        return expected

    lines = report_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        sha_match = re.match(r'SHA-256:\s*([a-fA-F0-9]{16,64})', line)
        if sha_match:
            sha_prefix = sha_match.group(1)
            for j in range(i - 1, max(i - 10, -1), -1):
                candidate = lines[j].strip()
                if candidate and candidate != line:
                    path_candidate = _clean_file_path(candidate)
                    if path_candidate:
                        expected[path_candidate] = sha_prefix
                        break
            i += 1
            continue
        i += 1

    return expected


def _clean_file_path(raw: str) -> str:
    cleaned = re.sub(r'^[-~*+#]+\s*', '', raw)
    cleaned = re.sub(r'[^\w\-_./\\ ]', '', cleaned)
    cleaned = cleaned.strip()
    return cleaned if len(cleaned) > 1 else ''


def _parse_archive_hash_from_report(report_text: str) -> str:
    if not report_text:
        return ''

    match = re.search(r'Archive\s+SHA-?256\s*[:\-]\s*([a-fA-F0-9]{16,128})', report_text)
    return match.group(1) if match else ''


def _parse_tsa_entries_from_report(report_text: str) -> list[dict]:
    entries: list[dict] = []
    if not report_text:
        return entries

    lines = report_text.split('\n')
    tsa_section = False

    for line in lines:
        stripped = line.strip()

        if re.search(r'TSA\s+Timestamps?', stripped, re.IGNORECASE):
            tsa_section = True
            continue

        if stripped.startswith('File ') or stripped.startswith('SHA-256'):
            tsa_section = False
            continue

        if not tsa_section:
            continue

        match = re.match(
            r'\[\s*(OK|SUCCESS|TIMEOUT|ERROR|REJECTED|FAIL)\s*\]\s*([^:]+)\s*:\s*(.*)',
            stripped,
            re.IGNORECASE,
        )
        if match:
            status_str = match.group(1).upper()
            status = 'PASS' if status_str in ('OK', 'SUCCESS') else 'FAIL'
            entries.append({
                'server_label': match.group(2).strip(),
                'signing_time': match.group(3).strip(),
                'status': status,
                'token_hex': '',
            })
            continue

        inner_match = re.match(
            r'\(\s*OK\s*\|\s*([^)]+)\s*\|\s*([^)]*)\s*\|\s*token:([a-fA-F0-9]+)\s*\)',
            stripped,
        )
        if inner_match:
            entries.append({
                'server_label': inner_match.group(1).strip(),
                'signing_time': inner_match.group(2).strip(),
                'status': 'PASS',
                'token_hex': inner_match.group(3).strip(),
            })

    return entries


def _check_file_hashes(
    result: VerificationReport,
    archive_path: Path,
    expected_hashes: dict[str, str],
    tsa_entries: list[dict],
) -> None:
    try:
        with ZipFile(archive_path, 'r') as zf:
            file_list = zf.namelist()
            result.files_total = len(file_list)

            for name in file_list:
                try:
                    with zf.open(name) as f:
                        sha256 = hashlib.sha256()
                        while True:
                            chunk = f.read(BUFFER_SIZE)
                            if not chunk:
                                break
                            sha256.update(chunk)
                        actual_hash = sha256.hexdigest()
                except Exception:
                    actual_hash = ''

                expected = expected_hashes.get(name, '')
                clean_name = _clean_file_path(name)
                if not expected and clean_name:
                    expected = expected_hashes.get(clean_name, '')

                if expected:
                    if actual_hash and actual_hash.startswith(expected):
                        status = 'PASS'
                        result.files_matched += 1
                    else:
                        status = 'MISMATCH'
                        result.files_mismatched += 1
                else:
                    status = 'PASS'
                    result.files_matched += 1

                detail = {
                    'path': name,
                    'status': status,
                    'sha256_archive': actual_hash[:32] if actual_hash else 'ERROR',
                    'sha256_report': expected[:32] if expected else '',
                }
                result.file_details.append(detail)

    except Exception as e:
        result.file_details.append({
            'path': str(archive_path),
            'status': 'ERROR',
            'error': str(e),
        })
        result.overall = 'FAIL'


def _check_tsa_timestamps(
    result: VerificationReport,
    archive_path: Path,
    expected_hashes: dict[str, str],
    tsa_entries: list[dict],
) -> None:
    result.tsa_total = len(tsa_entries)

    for entry in tsa_entries:
        verified = False

        if entry.get('token_hex'):
            try:
                if expected_hashes:
                    sample_hash = next((h for h in expected_hashes.values() if h), '')
                else:
                    try:
                        archive_hash, _ = hash_file(archive_path)
                        sample_hash = archive_hash
                    except Exception:
                        sample_hash = ''
                if sample_hash:
                    verified = verify_tsa_timestamp(entry['token_hex'], sample_hash)
            except Exception:
                verified = False

        if verified or entry.get('status') == 'PASS':
            result.tsa_valid += 1
        else:
            result.tsa_invalid += 1


def _determine_overall(result: VerificationReport) -> str:
    if not result.archive_hash_check:
        return 'FAIL'
    if result.files_mismatched > 0:
        return 'FAIL'
    if result.tsa_invalid > 0:
        return 'FAIL'
    return 'PASS'
