import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from signed_archive.models.metadata import BasicMetadata, DocumentMetadata, ImageMetadata, VideoMetadata
from signed_archive.utils.fs import classify_file_type


def _run_ffprobe(filepath: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(filepath)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def _extract_video_metadata(filepath: Path, probe: dict) -> VideoMetadata:
    fmt = probe.get("format", {})
    streams = probe.get("streams", [])

    video_stream = None
    audio_stream = None
    for s in streams:
        if s.get("codec_type") == "video" and video_stream is None:
            video_stream = s
        elif s.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = s

    duration = float(fmt.get("duration", 0))
    total_seconds = int(duration)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    ms = int((duration - total_seconds) * 100)

    duration_hms = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:02d}"

    fps = 0.0
    if video_stream:
        r_frame_rate = video_stream.get("r_frame_rate", "0/1")
        if "/" in r_frame_rate:
            num, den = r_frame_rate.split("/")
            if float(den) != 0:
                fps = float(num) / float(den)

    return VideoMetadata(
        duration_seconds=duration,
        duration_hms=duration_hms,
        frame_count=int(fmt.get("nb_frames", 0)) if fmt.get("nb_frames") else None,
        fps=fps,
        bitrate_bps=int(fmt.get("bit_rate", 0)) if fmt.get("bit_rate") else None,
        width=int(video_stream.get("width", 0)) if video_stream else 0,
        height=int(video_stream.get("height", 0)) if video_stream else 0,
        video_codec=video_stream.get("codec_name", "") if video_stream else "",
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        pixel_format=video_stream.get("pix_fmt", "") if video_stream else "",
    )


def _extract_image_metadata(filepath: Path, probe: dict) -> ImageMetadata:
    streams = probe.get("streams", [])
    fmt = probe.get("format", {})

    img_stream = None
    for s in streams:
        if s.get("codec_type") == "video":
            img_stream = s
            break

    exif_data = None
    exif_tags = fmt.get("tags", {})
    if exif_tags:
        exif_data = dict(exif_tags)

    return ImageMetadata(
        width=int(img_stream.get("width", 0)) if img_stream else 0,
        height=int(img_stream.get("height", 0)) if img_stream else 0,
        format=fmt.get("format_name", "").split(",")[0] if fmt.get("format_name") else "",
        pixel_format=img_stream.get("pix_fmt", "") if img_stream else "",
        bits_per_channel=img_stream.get("bits_per_raw_sample") if img_stream else None,
        color_space=img_stream.get("color_space") if img_stream else None,
        exif=exif_data,
    )


def _extract_document_metadata(filepath: Path) -> DocumentMetadata:
    ext = filepath.suffix.lower()
    doc = DocumentMetadata(format=ext.lstrip(".") if ext else "")

    if ext == ".pdf":
        try:
            result = subprocess.run(
                ["python", "-c", f'''
import re
with open(r"{filepath}", "rb") as f:
    content = f.read(1024 * 100)
    text = content.decode("latin-1", errors="ignore")
    for line in text.split("\\n"):
        if line.strip().startswith("/Creator"):
            print(f"Creator: {line.strip()}")
        if line.strip().startswith("/Author"):
            print(f"Author: {line.strip()}")
        if line.strip().startswith("/CreationDate"):
            print(f"CreationDate: {line.strip()}")
'''],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.startswith("Creator:"):
                        doc.creator = line.split(":", 1)[1].strip().lstrip("(").rstrip(")")
                    elif line.startswith("Author:"):
                        doc.author = line.split(":", 1)[1].strip().lstrip("(").rstrip(")")
                    elif line.startswith("CreationDate:"):
                        doc.creation_date = line.split(":", 1)[1].strip().lstrip("(").rstrip(")")
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["python", "-c", f'''
with open(r"{filepath}", "rb") as f:
    content = f.read(1024 * 1024)
    import re
    pages = re.findall(rb"/Type\\s*/Page[^s]", content)
    print(len(pages))
'''],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                doc.page_count = int(result.stdout.strip())
        except Exception:
            pass

    return doc


def extract_metadata(filepath: Path, skip_ffmpeg: bool = False) -> tuple[str, VideoMetadata | ImageMetadata | DocumentMetadata | BasicMetadata]:
    file_type = classify_file_type(filepath)
    ext = filepath.suffix.lower()

    if skip_ffmpeg:
        return file_type, BasicMetadata(extension=ext)

    if file_type in ("video", "image"):
        probe = _run_ffprobe(filepath)
        if probe:
            if file_type == "video":
                return file_type, _extract_video_metadata(filepath, probe)
            else:
                return file_type, _extract_image_metadata(filepath, probe)

    if file_type == "document":
        return file_type, _extract_document_metadata(filepath)

    return file_type, BasicMetadata(extension=ext)
