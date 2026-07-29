from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime, timezone

from signed_archive.models.metadata import BasicMetadata, DocumentMetadata, ImageMetadata, VideoMetadata


class FileStatus(str, Enum):
    PROCESSED = "processed"
    SKIPPED_PERMISSION = "skipped_permission"
    SKIPPED_LOCKED = "skipped_locked"
    ERROR = "error"


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    METADATA_CHANGED = "metadata_changed"


class TSAStatus(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass
class TimestampSignature:
    tsa_server_url: str
    tsa_server_label: str
    signing_time: str
    token_hex: str
    serial_number: int
    tsa_cert_subject: str
    tsa_cert_issuer: str
    digest_algorithm: str
    status: TSAStatus = TSAStatus.SUCCESS
    error_message: str | None = None


@dataclass
class FileRecord:
    relative_path: str
    file_size: int
    sha256: str
    md5: str
    modified_time: str
    file_type: str  # video / image / document / other
    metadata: VideoMetadata | ImageMetadata | DocumentMetadata | BasicMetadata = field(default_factory=BasicMetadata)
    tsa_timestamps: list[TimestampSignature] = field(default_factory=list)
    status: FileStatus = FileStatus.PROCESSED
    error_message: str | None = None


@dataclass
class RunState:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    input_directory: str = ""
    archive_sha256: str = ""
    archive_md5: str = ""
    archive_size: int = 0
    total_files: int = 0
    file_records: dict[str, FileRecord] = field(default_factory=dict)
    tsa_servers_used: list[str] = field(default_factory=list)
    config_hash: str = ""


@dataclass
class DeltaChange:
    change_type: ChangeType
    relative_path: str
    before_sha256: str | None = None
    after_sha256: str | None = None
    before_metadata: dict | None = None
    after_metadata: dict | None = None
    before_tsa_timestamps: list[TimestampSignature] | None = None
