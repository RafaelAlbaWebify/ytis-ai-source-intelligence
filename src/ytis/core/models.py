from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VideoRecord:
    video_id: str
    title: str
    upload_date: str = ""
    duration: str = ""
    webpage_url: str = ""


@dataclass
class TranscriptRecord:
    filename: str
    video_id: str
    title: str
    upload_date: str
    txt_file: str
    word_count: int
    char_count: int
