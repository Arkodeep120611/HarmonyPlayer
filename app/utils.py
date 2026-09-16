from __future__ import annotations

import os
import uuid
from pathlib import Path

from flask import current_app, request, url_for
from werkzeug.exceptions import Forbidden
from werkzeug.utils import secure_filename

try:
    from mutagen import File as MutagenFile
except Exception:  # pragma: no cover
    MutagenFile = None

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}


def expects_json() -> bool:
    if request.path.startswith("/api/"):
        return True
    best = request.accept_mimetypes.best
    return best == "application/json"


def allowed_audio_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_AUDIO_EXTENSIONS


def normalize_text(value: str | None, fallback: str) -> str:
    value = (value or "").strip()
    return value or fallback


def create_song_storage_path(user_id: int, original_filename: str) -> tuple[str, str]:
    extension = Path(original_filename).suffix.lower()
    base_name = secure_filename(Path(original_filename).stem) or "track"
    stored_name = f"{uuid.uuid4().hex}_{base_name}{extension}"
    relative_path = f"user_{user_id}/{stored_name}"
    absolute_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], f"user_{user_id}")
    os.makedirs(absolute_dir, exist_ok=True)
    absolute_path = os.path.abspath(os.path.join(current_app.config["UPLOAD_FOLDER"], relative_path))
    if not absolute_path.startswith(os.path.abspath(current_app.config["UPLOAD_FOLDER"]) + os.sep):
        raise Forbidden("Invalid upload destination.")
    return relative_path.replace("\\", "/"), absolute_path


def extract_audio_metadata(file_path: str, fallback_title: str, fallback_artist: str, fallback_album: str):
    title = fallback_title
    artist = fallback_artist
    album = fallback_album
    duration = None

    if MutagenFile is not None:
        audio = MutagenFile(file_path, easy=True)
        if audio is not None:
            title = normalize_text((audio.get("title") or [None])[0], title)
            artist = normalize_text((audio.get("artist") or [None])[0], artist)
            album = normalize_text((audio.get("album") or [None])[0], album)
            info = getattr(audio, "info", None)
            length = getattr(info, "length", None)
            if length is not None:
                duration = int(round(length))

    return title, artist, album, duration


def format_duration(seconds: int | None) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    minutes, remaining = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{remaining:02d}"
    return f"{minutes:02d}:{remaining:02d}"


def song_stream_url(song) -> str:
    return url_for("main.stream_song", song_id=song.id)


def song_to_dict(song) -> dict:
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "album": song.album,
        "filename": song.filename,
        "duration": song.duration,
        "duration_label": format_duration(song.duration),
        "created_at": song.created_at.isoformat() if song.created_at else None,
        "stream_url": song_stream_url(song),
    }


def playlist_to_dict(playlist, include_songs: bool = False) -> dict:
    payload = {
        "id": playlist.id,
        "name": playlist.name,
        "owner_id": playlist.owner_id,
        "created_at": playlist.created_at.isoformat() if playlist.created_at else None,
        "song_count": len(playlist.songs),
    }
    if include_songs:
        payload["songs"] = [song_to_dict(link.song) for link in playlist.songs]
    return payload


def settings_to_dict(settings) -> dict:
    return {
        "theme": settings.theme,
        "volume": settings.volume,
        "playback_speed": settings.playback_speed,
    }
