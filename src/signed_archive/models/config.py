from dataclasses import dataclass, field


@dataclass
class TSAServer:
    url: str
    label: str
    certificate_url: str | None = None
    enabled: bool = True


@dataclass
class TSAConfiguration:
    servers: list[TSAServer] = field(default_factory=list)
    min_servers_required: int = 1
    request_timeout_seconds: int = 30
    max_retries: int = 3
    retry_backoff_base_seconds: float = 2.0
    clock_skew_warning_threshold_seconds: float = 5.0
