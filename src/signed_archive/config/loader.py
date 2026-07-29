from pathlib import Path
import re

import yaml

from signed_archive.models.config import TSAServer, TSAConfiguration


URL_PATTERN = re.compile(r"^https?://")


def validate_config(config: TSAConfiguration) -> list[str]:
    errors: list[str] = []
    enabled_count = sum(1 for s in config.servers if s.enabled)

    for server in config.servers:
        if not URL_PATTERN.match(server.url):
            errors.append(f"Invalid TSA server URL: {server.url}")

    if config.min_servers_required < 1:
        errors.append("min_servers_required must be at least 1")
    if config.min_servers_required > enabled_count:
        errors.append(
            f"min_servers_required ({config.min_servers_required}) exceeds enabled server count ({enabled_count})"
        )

    return errors


def load_config(config_path: Path) -> TSAConfiguration:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raw = {}

    tsa_section = raw.get("tsa", raw)

    servers = []
    for s in tsa_section.get("servers", []):
        servers.append(TSAServer(
            url=s.get("url", ""),
            label=s.get("label", s.get("url", "")),
            certificate_url=s.get("certificate_url"),
            enabled=s.get("enabled", True),
        ))

    config = TSAConfiguration(
        servers=servers,
        min_servers_required=tsa_section.get("min_servers_required", 1),
        request_timeout_seconds=tsa_section.get("request_timeout_seconds", 30),
        max_retries=tsa_section.get("max_retries", 3),
        retry_backoff_base_seconds=tsa_section.get("retry_backoff_base_seconds", 2.0),
        clock_skew_warning_threshold_seconds=tsa_section.get("clock_skew_warning_threshold_seconds", 5.0),
    )

    errors = validate_config(config)
    if errors:
        raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    return config


def save_config(config: TSAConfiguration, config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "tsa": {
            "min_servers_required": config.min_servers_required,
            "request_timeout_seconds": config.request_timeout_seconds,
            "max_retries": config.max_retries,
            "retry_backoff_base_seconds": config.retry_backoff_base_seconds,
            "clock_skew_warning_threshold_seconds": config.clock_skew_warning_threshold_seconds,
            "servers": [
                {
                    "url": s.url,
                    "label": s.label,
                    "certificate_url": s.certificate_url,
                    "enabled": s.enabled,
                }
                for s in config.servers
            ],
        }
    }

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
