from __future__ import annotations

import os
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from werkzeug.utils import secure_filename
from wtforms import DecimalField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

from . import db
from .models import Playlist, PlaylistSong, Song, UserSettings
from .utils import (
    allowed_audio_file,
    create_song_storage_path,
    extract_audio_metadata,
    format_duration,
    playlist_to_dict,
    settings_to_dict,
    song_to_dict,
)

main_bp = Blueprint("main", __name__)


class UploadForm(FlaskForm):
    title = StringField("Title", validators=[Length(max=255)])
    artist = StringField("Artist", validators=[Length(max=255)])
    album = StringField("Album", validators=[Length(max=255)])
    file = FileField(
        "Audio File",
        validators=[FileRequired(), FileAllowed(["mp3", "wav", "ogg", "flac", "m4a"], "Audio files only.")],
    )
    submit = SubmitField("Upload")


class PlaylistForm(FlaskForm):
    name = StringField("Playlist name", validators=[DataRequired(), Length(min=1, max=120)])
    submit = SubmitField("Create playlist")


class SettingsForm(FlaskForm):
    theme = SelectField("Theme", choices=[("dark", "Dark"), ("light", "Light")], validators=[DataRequired()])
    volume = IntegerField("Volume", validators=[DataRequired(), NumberRange(min=0, max=100)])
    playback_speed = DecimalField(
        "Playback speed",
        validators=[DataRequired(), NumberRange(min=0.5, max=2.0)],
        places=2,
    )
    submit = SubmitField("Save settings")


def _owned_playlists():
    return current_user.playlists.order_by(Playlist.created_at.desc()).all()


def _owned_songs():
    return current_user.songs.order_by(Song.created_at.desc()).all()


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.library"))
    return render_template("index.html", page_title="HarmonyPlayer")


@main_bp.route("/library")
@login_required
def library():
    songs = _owned_songs()
    playlists = _owned_playlists()
    return render_template(
        "library.html",
        page_title="Library",
        songs=[song_to_dict(song) for song in songs],
        playlists=[playlist_to_dict(pl) for pl in playlists],
        upload_form=UploadForm(),
        playlist_form=PlaylistForm(),
        song_count=len(songs),
        playlist_count=len(playlists),
    )


@main_bp.route("/playlists", methods=["GET", "POST"])
@login_required
def playlists():
    form = PlaylistForm()
    if form.validate_on_submit():
        playlist = Playlist(name=form.name.data.strip(), owner_id=current_user.id)
        db.session.add(playlist)
        db.session.commit()
        flash("Playlist created.", "success")
        return redirect(url_for("main.playlists"))

    playlist_rows = [
        playlist_to_dict(playlist)
        for playlist in _owned_playlists()
    ]
    return render_template(
        "playlist.html",
        page_title="Playlists",
        playlists=playlist_rows,
        form=form,
        mode="index",
    )


@main_bp.route("/playlists/<int:playlist_id>")
@login_required
def playlist_detail(playlist_id: int):
    playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first_or_404()
    all_songs = _owned_songs()
    form = PlaylistForm()
    form.name.data = playlist.name
    return render_template(
        "playlist.html",
        page_title=playlist.name,
        playlist=playlist_to_dict(playlist, include_songs=True),
        playlists=[playlist_to_dict(pl) for pl in _owned_playlists()],
        available_songs=[song_to_dict(song) for song in all_songs],
        mode="detail",
        form=form,
    )


@main_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    settings = current_user.settings or UserSettings(user_id=current_user.id)
    form = SettingsForm()
    form.theme.data = settings.theme
    form.volume.data = settings.volume
    form.playback_speed.data = settings.playback_speed
    if form.validate_on_submit():
        settings.theme = form.theme.data
        settings.volume = int(form.volume.data)
        settings.playback_speed = float(form.playback_speed.data)
        current_user.settings = settings
        db.session.add(settings)
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("main.settings"))
    return render_template(
        "settings.html",
        page_title="Settings",
        form=form,
        account=current_user,
        settings=settings_to_dict(settings),
    )


@main_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    form = UploadForm()
    if not form.validate_on_submit():
        flash("Upload failed. Check the file and metadata fields.", "error")
        return redirect(url_for("main.library"))

    upload_file = form.file.data
    original_name = secure_filename(upload_file.filename or "")
    if not original_name or not allowed_audio_file(original_name):
        flash("Only MP3, WAV, OGG, FLAC, and M4A files are allowed.", "error")
        return redirect(url_for("main.library"))

    relative_path, absolute_path = create_song_storage_path(current_user.id, original_name)
    upload_file.save(absolute_path)

    fallback_title = form.title.data.strip() if form.title.data else Path(original_name).stem
    fallback_artist = form.artist.data.strip() if form.artist.data else "Unknown Artist"
    fallback_album = form.album.data.strip() if form.album.data else "Unknown Album"
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
    flash(f"Uploaded {song.title}.", "success")
    return redirect(url_for("main.library"))


@main_bp.route("/media/<int:song_id>")
@login_required
def stream_song(song_id: int):
    song = Song.query.filter_by(id=song_id, uploaded_by=current_user.id).first_or_404()
    base_folder = os.path.abspath(current_app.config["UPLOAD_FOLDER"])
    absolute_path = os.path.abspath(os.path.join(base_folder, song.filepath))
    if not absolute_path.startswith(base_folder + os.sep):
        return "", 403
    if not os.path.exists(absolute_path):
        return "", 404

    mimetype = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
    }.get(Path(absolute_path).suffix.lower(), "application/octet-stream")

    return send_file(
        absolute_path,
        mimetype=mimetype,
        conditional=True,
        as_attachment=False,
        max_age=0,
    )
