import logging
from datetime import datetime, timezone
from pathlib import Path


def init_run_logger(output_dir: Path) -> logging.Logger:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_file = output_dir / f"run_{timestamp}.log"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("signed_archive")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")
    fh.setFormatter(formatter)

    logger.addHandler(fh)
    return logger


def get_run_logger() -> logging.Logger:
    return logging.getLogger("signed_archive")
