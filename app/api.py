from __future__ import annotations

import os
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from werkzeug.exceptions import BadRequest, Forbidden

from . import db
from .models import Playlist, PlaylistSong, Song, UserSettings
from .routes import UploadForm
from .utils import (
    allowed_audio_file,
    create_song_storage_path,
    extract_audio_metadata,
    playlist_to_dict,
    settings_to_dict,
    song_to_dict,
)

api_bp = Blueprint("api", __name__)


def api_error(message: str, status_code: int):
    return jsonify({"error": message, "status": status_code}), status_code


def owned_song_or_404(song_id: int) -> Song:
    song = Song.query.filter_by(id=song_id, uploaded_by=current_user.id).first()
    if song is None:
        raise BadRequest("Song not found.")
    return song


def owned_playlist_or_404(playlist_id: int) -> Playlist:
    playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first()
    if playlist is None:
        raise BadRequest("Playlist not found.")
    return playlist


@api_bp.errorhandler(BadRequest)
def handle_bad_request(error):
    return api_error(str(error).replace("400 Bad Request: ", ""), 400)


@api_bp.errorhandler(Forbidden)
def handle_forbidden(error):
    return api_error(str(error).replace("403 Forbidden: ", ""), 403)


@api_bp.route("/songs", methods=["GET"])
@login_required
def songs():
    songs = Song.query.filter_by(uploaded_by=current_user.id).order_by(Song.created_at.desc()).all()
    return jsonify({"songs": [song_to_dict(song) for song in songs], "count": len(songs)})


@api_bp.route("/songs/<int:song_id>", methods=["GET"])
@login_required
def song_detail(song_id: int):
    song = Song.query.filter_by(id=song_id, uploaded_by=current_user.id).first()
    if song is None:
        return api_error("Song not found.", 404)
    return jsonify(song_to_dict(song))


@api_bp.route("/playlists", methods=["GET"])
@login_required
def playlists():
    playlists = Playlist.query.filter_by(owner_id=current_user.id).order_by(Playlist.created_at.desc()).all()
    return jsonify({"playlists": [playlist_to_dict(pl) for pl in playlists], "count": len(playlists)})


@api_bp.route("/playlists", methods=["POST"])
@login_required
def create_playlist():
    payload = request.get_json(silent=True) or request.form
    name = (payload.get("name") or "").strip()
    if not name:
        return api_error("Playlist name is required.", 400)
    playlist = Playlist(name=name, owner_id=current_user.id)
    db.session.add(playlist)
    db.session.commit()
    return jsonify(playlist_to_dict(playlist)), 201


@api_bp.route("/playlists/<int:playlist_id>", methods=["PUT"])
@login_required
def update_playlist(playlist_id: int):
    playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first()
    if playlist is None:
        return api_error("Playlist not found.", 404)
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return api_error("Playlist name is required.", 400)
    playlist.name = name
    db.session.commit()
    return jsonify(playlist_to_dict(playlist))


@api_bp.route("/playlists/<int:playlist_id>", methods=["DELETE"])
@login_required
def delete_playlist(playlist_id: int):
    playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first()
    if playlist is None:
        return api_error("Playlist not found.", 404)
    db.session.delete(playlist)
    db.session.commit()
    return jsonify({"message": "Playlist deleted."})


@api_bp.route("/playlists/<int:playlist_id>/songs", methods=["POST"])
@login_required
def add_playlist_songs(playlist_id: int):
    playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first()
    if playlist is None:
        return api_error("Playlist not found.", 404)
    payload = request.get_json(silent=True) or request.form
    raw_ids = payload.get("song_ids")
    if raw_ids is None:
        raw_ids = payload.get("song_id")
    if raw_ids is None:
        return api_error("At least one song ID is required.", 400)

    if isinstance(raw_ids, int):
        song_ids = [raw_ids]
    elif isinstance(raw_ids, str):
        if "," in raw_ids:
            song_ids = [int(item) for item in raw_ids.split(",") if item.strip()]
        else:
            song_ids = [int(raw_ids)]
    else:
        song_ids = [int(item) for item in list(raw_ids)]

    existing_ids = {link.song_id for link in playlist.songs}
    added = 0
    skipped = 0
    next_position = (max((link.position for link in playlist.songs), default=0) + 1) if playlist.songs else 1

    for song_id in song_ids:
        song = Song.query.filter_by(id=song_id, uploaded_by=current_user.id).first()
        if song is None:
            return api_error(f"Song {song_id} not found.", 404)
        if song_id in existing_ids:
            skipped += 1
            continue
        playlist_song = PlaylistSong(playlist_id=playlist.id, song_id=song.id, position=next_position)
        next_position += 1
        db.session.add(playlist_song)
        existing_ids.add(song_id)
        added += 1

    db.session.commit()
    return jsonify({"message": "Songs updated.", "added": added, "skipped": skipped, "playlist": playlist_to_dict(playlist, include_songs=True)})


@api_bp.route("/playlists/<int:playlist_id>/songs/<int:song_id>", methods=["DELETE"])
@login_required
def remove_playlist_song(playlist_id: int, song_id: int):
    playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first()
    if playlist is None:
        return api_error("Playlist not found.", 404)
    link = PlaylistSong.query.filter_by(playlist_id=playlist.id, song_id=song_id).first()
    if link is None:
        return api_error("Song is not in that playlist.", 404)
    db.session.delete(link)
    db.session.commit()
    return jsonify({"message": "Song removed from playlist."})


@api_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    form = UploadForm()
    if not form.validate_on_submit():
        return api_error("Upload validation failed.", 400)

    upload_file = form.file.data
    original_name = Path(upload_file.filename or "").name
    if not original_name or not allowed_audio_file(original_name):
        return api_error("Unsupported audio format.", 400)

    relative_path, absolute_path = create_song_storage_path(current_user.id, original_name)
    upload_file.save(absolute_path)

    fallback_title = (form.title.data or "").strip() or Path(original_name).stem
    fallback_artist = (form.artist.data or "").strip() or "Unknown Artist"
    fallback_album = (form.album.data or "").strip() or "Unknown Album"
    title, artist, album, duration = extract_audio_metadata(
        absolute_path,
        fallback_title=fallback_title,
        fallback_artist=fallback_artist,
        fallback_album=fallback_album,
    )

    song = Song(
        title=title,
        artist=artist,
        album=album,
        filename=original_name,
        filepath=relative_path,
        duration=duration,
        uploaded_by=current_user.id,
    )
    db.session.add(song)
    db.session.commit()
    return jsonify(song_to_dict(song)), 201


@api_bp.route("/settings", methods=["GET"])
@login_required
def get_settings():
    settings = current_user.settings or UserSettings(user_id=current_user.id)
    if settings.id is None:
        db.session.add(settings)
        db.session.commit()
    return jsonify(settings_to_dict(settings))


@api_bp.route("/settings", methods=["PUT"])
@login_required
def update_settings():
    payload = request.get_json(silent=True) or {}
    settings = current_user.settings or UserSettings(user_id=current_user.id)

    theme = payload.get("theme", settings.theme)
    if theme not in {"dark", "light"}:
        return api_error("Theme must be dark or light.", 400)

    try:
        volume = int(payload.get("volume", settings.volume))
        playback_speed = float(payload.get("playback_speed", settings.playback_speed))
    except (TypeError, ValueError):
        return api_error("Volume and playback speed must be numeric.", 400)

    if not 0 <= volume <= 100:
        return api_error("Volume must be between 0 and 100.", 400)
    if not 0.5 <= playback_speed <= 2.0:
        return api_error("Playback speed must be between 0.5 and 2.0.", 400)

    settings.theme = theme
    settings.volume = volume
    settings.playback_speed = playback_speed
    current_user.settings = settings
    db.session.add(settings)
    db.session.commit()
    return jsonify(settings_to_dict(settings))
