from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin

from . import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    songs = db.relationship(
        "Song",
        back_populates="uploader",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    playlists = db.relationship(
        "Playlist",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    settings = db.relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        from werkzeug.security import generate_password_hash

        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        from werkzeug.security import check_password_hash

        return check_password_hash(self.password_hash, password)


class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False, default="Unknown Artist")
    album = db.Column(db.String(255), nullable=False, default="Unknown Album")
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False, unique=True)
    duration = db.Column(db.Integer, nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    uploader = db.relationship("User", back_populates="songs")
    playlist_links = db.relationship(
        "PlaylistSong",
        back_populates="song",
        cascade="all, delete-orphan",
    )


class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    owner = db.relationship("User", back_populates="playlists")
    songs = db.relationship(
        "PlaylistSong",
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistSong.position",
    )


class PlaylistSong(db.Model):
    __table_args__ = (db.UniqueConstraint("playlist_id", "song_id", name="uq_playlist_song"),)

    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey("playlist.id"), nullable=False, index=True)
    song_id = db.Column(db.Integer, db.ForeignKey("song.id"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    playlist = db.relationship("Playlist", back_populates="songs")
    song = db.relationship("Song", back_populates="playlist_links")


class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False, index=True)
    theme = db.Column(db.String(16), nullable=False, default="dark")
    volume = db.Column(db.Integer, nullable=False, default=70)
    playback_speed = db.Column(db.Float, nullable=False, default=1.0)

    user = db.relationship("User", back_populates="settings")
