from dataclasses import dataclass, field

from signed_archive.models.run_state import FileRecord, TimestampSignature


@dataclass
class ReportData:
    run_id: str = ""
    run_timestamp: str = ""
    input_directory: str = ""
    is_first_run: bool = True
    archive_sha256: str = ""
    archive_md5: str = ""
    archive_size: int = 0
    total_files: int = 0
    file_records: list[FileRecord] = field(default_factory=list)
    changes: list = field(default_factory=list)
    tsa_servers_used: list[str] = field(default_factory=list)
    skipped_files: int = 0
    error_files: int = 0
