import os
import shutil
from pathlib import Path
from typing import Iterator


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".flv", ".3gp"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".gif", ".bmp", ".webp", ".svg", ".heic", ".heif"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".odt", ".txt", ".rtf", ".xlsx", ".pptx", ".csv", ".html", ".xml", ".md"}


def classify_file_type(filepath: Path) -> str:
    ext = filepath.suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    return "other"


def walk_directory(
    directory: Path, follow_symlinks: bool = True, skip_symlinks: bool = False
) -> Iterator[Path]:
    for root, dirs, files in os.walk(str(directory), followlinks=follow_symlinks):
        dirs[:] = [d for d in dirs if d != ".signed_archive"]
        root_path = Path(root)
        for name in files:
            filepath = root_path / name
            if filepath.is_symlink() and skip_symlinks:
                continue
            yield filepath


def check_ffprobe() -> bool:
    return shutil.which("ffprobe") is not None
