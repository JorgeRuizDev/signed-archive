from dataclasses import dataclass, field


@dataclass
class VideoMetadata:
    duration_seconds: float = 0.0
    duration_hms: str = ""
    frame_count: int | None = None
    fps: float = 0.0
    bitrate_bps: int | None = None
    width: int = 0
    height: int = 0
    video_codec: str = ""
    audio_codec: str | None = None
    pixel_format: str = ""


@dataclass
class ImageMetadata:
    width: int = 0
    height: int = 0
    format: str = ""
    pixel_format: str = ""
    bits_per_channel: int | None = None
    color_space: str | None = None
    exif: dict | None = None


@dataclass
class DocumentMetadata:
    page_count: int | None = None
    author: str | None = None
    creator: str | None = None
    creation_date: str | None = None
    format: str = ""


@dataclass
class BasicMetadata:
    mime_type: str | None = None
    extension: str = ""
    notes: str = "no specialized metadata available"
