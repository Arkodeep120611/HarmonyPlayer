import os
import sys
import random
from PySide6.QtCore import Qt, QUrl, QSettings, QSize, QStandardPaths
from PySide6.QtGui import QAction, QShortcut, QKeySequence
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
    QCheckBox,
    QMessageBox,
)


class MusicPlayerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Music Player")
        self.resize(1040, 680)

        # Persistent settings
        self.settings = QSettings("ArkodeepApps", "PythonMusicPlayer")

        # Audio engine setup
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

        # Seek handling flags
        self.is_user_seeking = False
        self.seek_supported_for_current_track = False

        # Playlist state
        self.loaded_file_paths = set()

        # Playback modes
        self.shuffle_enabled = False
        self.repeat_mode = "off"  # off, all, one

        # Theme mode
        self.dark_theme_enabled = False

        # Central container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Header
        self.now_playing_label = QLabel("Now Playing: Nothing loaded")
        self.now_playing_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.now_playing_label)

        # Playlist area
        self.playlist_widget = QListWidget()
        self.playlist_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.playlist_widget.setAcceptDrops(True)
        self.playlist_widget.setDragDropMode(QListWidget.DropOnly)
        self.playlist_widget.viewport().setAcceptDrops(True)
        self.playlist_widget.setDefaultDropAction(Qt.CopyAction)
        main_layout.addWidget(self.playlist_widget)
        self.playlist_widget.itemDoubleClicked.connect(self.play_item_from_double_click)

        self.setAcceptDrops(True)

        # Seek row container
        self.seek_row_widget = QWidget()
        seek_layout = QHBoxLayout()
        seek_layout.setContentsMargins(0, 0, 0, 0)
        self.seek_row_widget.setLayout(seek_layout)

        self.current_time_label = QLabel("00:00")
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.total_time_label = QLabel("00:00")

        seek_layout.addWidget(self.current_time_label)
        seek_layout.addWidget(self.seek_slider)
        seek_layout.addWidget(self.total_time_label)
        main_layout.addWidget(self.seek_row_widget)
        self.seek_row_widget.hide()

        # Controls row
        controls_layout = QHBoxLayout()
        self.prev_button = QPushButton("⏮ Previous")
        self.play_button = QPushButton("▶ Play")
        self.pause_button = QPushButton("⏸ Pause")
        self.stop_button = QPushButton("⏹ Stop")
        self.next_button = QPushButton("Next ⏭")
        self.remove_button = QPushButton("🗑 Remove Selected")

        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.next_button)
        controls_layout.addWidget(self.remove_button)
        main_layout.addLayout(controls_layout)

        # Mode controls row
        mode_layout = QHBoxLayout()
        self.shuffle_button = QPushButton("Shuffle: Off")
        self.repeat_button = QPushButton("Repeat: Off")
        self.theme_button = QPushButton("Theme: Light")
        mode_layout.addWidget(self.shuffle_button)
        mode_layout.addWidget(self.repeat_button)
        mode_layout.addWidget(self.theme_button)
        main_layout.addLayout(mode_layout)

        # Audio controls row (volume + mute + speed)
        audio_controls_layout = QHBoxLayout()

        volume_label = QLabel("Volume")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)

        self.mute_checkbox = QCheckBox("Mute")

        speed_label = QLabel("Speed")
        self.speed_spinbox = QDoubleSpinBox()
        self.speed_spinbox.setRange(0.5, 2.0)
        self.speed_spinbox.setSingleStep(0.1)
        self.speed_spinbox.setDecimals(1)
        self.speed_spinbox.setValue(1.0)
        self.speed_spinbox.setSuffix("x")

        audio_controls_layout.addWidget(volume_label)
        audio_controls_layout.addWidget(self.volume_slider)
        audio_controls_layout.addWidget(self.mute_checkbox)
        audio_controls_layout.addSpacing(16)
        audio_controls_layout.addWidget(speed_label)
        audio_controls_layout.addWidget(self.speed_spinbox)
        main_layout.addLayout(audio_controls_layout)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Build menu
        self._create_menu()

        # Wire playback controls
        self.play_button.clicked.connect(self.play_selected_song)
        self.pause_button.clicked.connect(self.toggle_pause_resume)
        self.stop_button.clicked.connect(self.stop_song)
        self.next_button.clicked.connect(self.play_next_song)
        self.prev_button.clicked.connect(self.play_previous_song)
        self.remove_button.clicked.connect(self.remove_selected_tracks)

        # Wire mode controls
        self.shuffle_button.clicked.connect(self.toggle_shuffle)
        self.repeat_button.clicked.connect(self.cycle_repeat_mode)
        self.theme_button.clicked.connect(self.toggle_theme)

        # Wire audio controls
        self.volume_slider.valueChanged.connect(self.change_volume)
        self.mute_checkbox.toggled.connect(self.toggle_mute)
        self.speed_spinbox.valueChanged.connect(self.change_playback_speed)

        # Player signals
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)

        # Seek slider interactions
        self.seek_slider.sliderPressed.connect(self.on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self.on_seek_released)
        self.seek_slider.sliderMoved.connect(self.on_seek_moved)

        # Keyboard shortcuts
        self._setup_shortcuts()

        # Load persisted settings
        self.load_settings()

    def _create_menu(self):
        file_menu = self.menuBar().addMenu("File")

        open_action = QAction("Open Music Files...", self)
        open_action.triggered.connect(self.open_files)
        file_menu.addAction(open_action)

        clear_action = QAction("Clear Playlist", self)
        clear_action.triggered.connect(self.clear_playlist)
        file_menu.addAction(clear_action)

        remove_selected_action = QAction("Remove Selected", self)
        remove_selected_action.triggered.connect(self.remove_selected_tracks)
        file_menu.addAction(remove_selected_action)

        file_menu.addSeparator()

        save_playlist_action = QAction("Save Playlist (.m3u)...", self)
        save_playlist_action.triggered.connect(self.save_playlist_m3u)
        file_menu.addAction(save_playlist_action)

        load_playlist_action = QAction("Load Playlist (.m3u)...", self)
        load_playlist_action.triggered.connect(self.load_playlist_m3u)
        file_menu.addAction(load_playlist_action)

        file_menu.addSeparator()

        # Explicit Quit action. QKeySequence.StandardKey.Quit resolves to
        # Ctrl+Q on Linux/Windows and Cmd+Q on macOS automatically.
        # MenuRole.QuitRole tells macOS to relocate this into the app menu
        # (under "Python Music Player") instead of leaving it in "File".
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Quit))
        quit_action.setMenuRole(QAction.MenuRole.QuitRole)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = self.menuBar().addMenu("View")
        toggle_theme_action = QAction("Toggle Light/Dark Theme", self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(toggle_theme_action)

        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About", self)
        # MenuRole.AboutRole relocates this into the macOS app menu too.
        # On Linux it just stays under Help, which is the native convention there.
        about_action.setMenuRole(QAction.MenuRole.AboutRole)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def _setup_shortcuts(self):
        self.shortcut_space = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.shortcut_space.activated.connect(self.play_pause_shortcut_action)

        # Qt automatically remaps "Ctrl" to "Cmd" in QKeySequence on macOS,
        # so these strings work as-is on both Linux and macOS.
        self.shortcut_next = QShortcut(QKeySequence("Ctrl+Right"), self)
        self.shortcut_next.activated.connect(self.play_next_song)

        self.shortcut_prev = QShortcut(QKeySequence("Ctrl+Left"), self)
        self.shortcut_prev.activated.connect(self.play_previous_song)

        self.shortcut_delete = QShortcut(QKeySequence(Qt.Key_Delete), self)
        self.shortcut_delete.activated.connect(self.remove_selected_tracks)

        self.shortcut_mute = QShortcut(QKeySequence("Ctrl+M"), self)
        self.shortcut_mute.activated.connect(
            lambda: self.mute_checkbox.setChecked(not self.mute_checkbox.isChecked())
        )

        self.shortcut_theme = QShortcut(QKeySequence("Ctrl+T"), self)
        self.shortcut_theme.activated.connect(self.toggle_theme)

    # ---------- Utility messaging ----------

    def set_now_playing(self, text):
        self.now_playing_label.setText(text)

    def set_status(self, text, timeout_ms=3000):
        self.statusBar().showMessage(text, timeout_ms)

    # ---------- Theme handling ----------

    def apply_theme(self):
        if self.dark_theme_enabled:
            self.setStyleSheet(
                """
                QMainWindow, QWidget {
                    background-color: #1e1e1e;
                    color: #f0f0f0;
                }
                QPushButton {
                    background-color: #2d2d2d;
                    color: #f0f0f0;
                    border: 1px solid #555;
                    padding: 6px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                }
                QListWidget {
                    background-color: #252525;
                    color: #f0f0f0;
                    border: 1px solid #555;
                }
                QSlider::groove:horizontal {
                    height: 6px;
                    background: #444;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #bbbbbb;
                    width: 12px;
                    margin: -4px 0;
                    border-radius: 6px;
                }
                QMenuBar, QMenu {
                    background-color: #2a2a2a;
                    color: #f0f0f0;
                }
                QStatusBar {
                    background-color: #2a2a2a;
                    color: #f0f0f0;
                }
                """
            )
            self.theme_button.setText("Theme: Dark")
            self.set_status("Dark theme enabled")
        else:
            self.setStyleSheet("")
            self.theme_button.setText("Theme: Light")
            self.set_status("Light theme enabled")

    def toggle_theme(self):
        self.dark_theme_enabled = not self.dark_theme_enabled
        self.apply_theme()

    # ---------- About ----------

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "About Python Music Player",
            (
                "Python Music Player\n\n"
                "Built with PySide6.\n\n"
                "Features:\n"
                "- Playlist add/remove + drag & drop\n"
                "- Play/Pause/Stop/Next/Previous\n"
                "- Shuffle + Repeat (Off/All/One)\n"
                "- Conditional seek bar support\n"
                "- Save/Load .m3u playlists\n"
                "- Volume, mute, playback speed\n"
                "- Keyboard shortcuts\n"
                "- Persistent settings"
            ),
        )

    # ---------- Settings persistence ----------

    def load_settings(self):
        saved_size = self.settings.value("window/size")
        if isinstance(saved_size, QSize):
            self.resize(saved_size)

        saved_volume = self.settings.value("audio/volume", 50, type=int)
        saved_volume = max(0, min(100, saved_volume))
        self.volume_slider.setValue(saved_volume)
        self.audio_output.setVolume(saved_volume / 100.0)

        saved_muted = self.settings.value("audio/muted", False, type=bool)
        self.mute_checkbox.setChecked(saved_muted)
        self.audio_output.setMuted(saved_muted)

        saved_speed = self.settings.value("audio/speed", 1.0, type=float)
        if saved_speed < 0.5 or saved_speed > 2.0:
            saved_speed = 1.0
        self.speed_spinbox.setValue(saved_speed)
        self.player.setPlaybackRate(saved_speed)

        self.shuffle_enabled = self.settings.value("playback/shuffle", False, type=bool)
        self.shuffle_button.setText("Shuffle: On" if self.shuffle_enabled else "Shuffle: Off")

        saved_repeat = self.settings.value("playback/repeat_mode", "off", type=str)
        if saved_repeat not in {"off", "all", "one"}:
            saved_repeat = "off"
        self.repeat_mode = saved_repeat
        self._refresh_repeat_button_text()

        self.dark_theme_enabled = self.settings.value("ui/dark_theme", False, type=bool)
        self.apply_theme()

        self.set_status("Settings loaded")

    def save_settings(self):
        self.settings.setValue("window/size", self.size())
        self.settings.setValue("audio/volume", self.volume_slider.value())
        self.settings.setValue("audio/muted", self.mute_checkbox.isChecked())
        self.settings.setValue("audio/speed", float(self.speed_spinbox.value()))
        self.settings.setValue("playback/shuffle", self.shuffle_enabled)
        self.settings.setValue("playback/repeat_mode", self.repeat_mode)
        self.settings.setValue("ui/dark_theme", self.dark_theme_enabled)

    def _refresh_repeat_button_text(self):
        if self.repeat_mode == "off":
            self.repeat_button.setText("Repeat: Off")
        elif self.repeat_mode == "all":
            self.repeat_button.setText("Repeat: All")
        else:
            self.repeat_button.setText("Repeat: One")

    def closeEvent(self, event):
        self.save_settings()
        self.set_status("Settings saved", 1000)
        super().closeEvent(event)

    # ---------- Drag & drop ----------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        file_paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_paths.append(url.toLocalFile())

        self.add_files_from_paths(file_paths)
        event.acceptProposedAction()

    # ---------- Playlist helpers ----------

    def is_supported_audio_file(self, path):
        supported_exts = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
        ext = os.path.splitext(path)[1].lower()
        return ext in supported_exts

    def add_song_path_to_playlist(self, path):
        if not path or not self.is_supported_audio_file(path):
            return False

        normalized_path = os.path.normpath(path)
        if normalized_path in self.loaded_file_paths:
            return False

        filename = os.path.basename(path)
        item = QListWidgetItem(filename)
        item.setData(Qt.UserRole, path)
        self.playlist_widget.addItem(item)
        self.loaded_file_paths.add(normalized_path)
        return True

    def add_files_from_paths(self, file_paths):
        if not file_paths:
            return

        added_count = 0
        skipped_count = 0

        for path in file_paths:
            if self.add_song_path_to_playlist(path):
                added_count += 1
            else:
                skipped_count += 1

        if added_count > 0 and skipped_count == 0:
            self.set_now_playing(f"Now Playing: Added {added_count} song(s)")
            self.set_status(f"Added {added_count} file(s)")
        elif added_count > 0 and skipped_count > 0:
            self.set_now_playing(
                f"Now Playing: Added {added_count}, skipped {skipped_count} unsupported/duplicate file(s)"
            )
            self.set_status(f"Added {added_count}, skipped {skipped_count}")
        else:
            self.set_now_playing("Now Playing: No new supported files were added")
            self.set_status("No supported files added")

    def open_files(self):
        # Default to the platform's native Music folder (~/Music on both
        # macOS and Linux) instead of an unspecified/last-used directory.
        default_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.MusicLocation
        )
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Music Files",
            default_dir,
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a);;All Files (*)",
        )
        self.add_files_from_paths(file_paths)

    def clear_playlist(self):
        self.player.stop()
        self.playlist_widget.clear()
        self.loaded_file_paths.clear()

        self.seek_supported_for_current_track = False
        self.seek_row_widget.hide()
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setValue(0)
        self.current_time_label.setText("00:00")
        self.total_time_label.setText("00:00")

        self.set_now_playing("Now Playing: Playlist cleared")
        self.set_status("Playlist cleared")

    def remove_selected_tracks(self):
        selected_items = self.playlist_widget.selectedItems()
        if not selected_items:
            self.set_now_playing("Now Playing: No tracks selected to remove")
            self.set_status("No tracks selected")
            return

        removed_count = 0
        for item in selected_items:
            song_path = item.data(Qt.UserRole)
            if song_path:
                self.loaded_file_paths.discard(os.path.normpath(song_path))
            self.playlist_widget.takeItem(self.playlist_widget.row(item))
            removed_count += 1

        if self.playlist_widget.count() == 0:
            self.player.stop()
            self.seek_supported_for_current_track = False
            self.seek_row_widget.hide()
            self.seek_slider.setRange(0, 0)
            self.seek_slider.setValue(0)
            self.current_time_label.setText("00:00")
            self.total_time_label.setText("00:00")
            self.set_now_playing("Now Playing: Playlist is empty after removal")
        else:
            self.set_now_playing(f"Now Playing: Removed {removed_count} track(s)")

        self.set_status(f"Removed {removed_count} track(s)")

    # ---------- Save / Load .m3u ----------

    def save_playlist_m3u(self):
        total_items = self.playlist_widget.count()
        if total_items == 0:
            self.set_now_playing("Now Playing: Playlist is empty, nothing to save")
            self.set_status("Save cancelled: empty playlist")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Playlist", "", "M3U Playlist (*.m3u);;All Files (*)"
        )
        if not file_path:
            return

        if not file_path.lower().endswith(".m3u"):
            file_path += ".m3u"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for i in range(total_items):
                    item = self.playlist_widget.item(i)
                    song_path = item.data(Qt.UserRole)
                    if song_path:
                        f.write(f"{song_path}\n")
            self.set_now_playing(f"Now Playing: Playlist saved to {os.path.basename(file_path)}")
            self.set_status("Playlist saved")
        except Exception as e:
            self.set_now_playing(f"Now Playing: Failed to save playlist ({e})")
            self.set_status("Playlist save failed")

    def load_playlist_m3u(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Playlist", "", "M3U Playlist (*.m3u);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.set_now_playing(f"Now Playing: Failed to load playlist ({e})")
            self.set_status("Playlist load failed")
            return

        self.clear_playlist()

        base_dir = os.path.dirname(file_path)
        added_count = 0
        missing_count = 0

        for line in lines:
            if line.startswith("#"):
                continue

            candidate_path = line
            if not os.path.isabs(candidate_path):
                candidate_path = os.path.normpath(os.path.join(base_dir, candidate_path))

            if os.path.exists(candidate_path):
                if self.add_song_path_to_playlist(candidate_path):
                    added_count += 1
            else:
                missing_count += 1

        if added_count > 0 and missing_count == 0:
            self.set_now_playing(f"Now Playing: Loaded {added_count} song(s) from playlist")
        elif added_count > 0 and missing_count > 0:
            self.set_now_playing(f"Now Playing: Loaded {added_count}, missing {missing_count} file(s)")
        else:
            self.set_now_playing("Now Playing: No valid songs found in playlist")

        self.set_status(f"Playlist loaded ({added_count} added, {missing_count} missing)")

    # ---------- Playback controls ----------

    def play_item_from_double_click(self, item):
        self.playlist_widget.setCurrentRow(self.playlist_widget.row(item))
        self.play_selected_song()

    def play_selected_song(self):
        current_item = self.playlist_widget.currentItem()
        if current_item is None:
            self.set_now_playing("Now Playing: Please select a song first")
            self.set_status("No song selected")
            return

        song_name = current_item.text()
        song_path = current_item.data(Qt.UserRole)
        if not song_path:
            self.set_now_playing("Now Playing: Invalid file path")
            self.set_status("Invalid file path")
            return

        self.seek_supported_for_current_track = False
        self.seek_row_widget.hide()
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setValue(0)
        self.current_time_label.setText("00:00")
        self.total_time_label.setText("00:00")

        self.player.setSource(QUrl.fromLocalFile(song_path))
        self.player.play()
        self.set_now_playing(f"Now Playing: {song_name}")
        self.set_status(f"Playing: {song_name}")

    def play_pause_shortcut_action(self):
        state = self.player.playbackState()
        if state in (QMediaPlayer.PlayingState, QMediaPlayer.PausedState):
            self.toggle_pause_resume()
        else:
            if self.playlist_widget.currentItem() is None and self.playlist_widget.count() > 0:
                self.playlist_widget.setCurrentRow(0)
            self.play_selected_song()

    def toggle_pause_resume(self):
        state = self.player.playbackState()

        if state == QMediaPlayer.PlayingState:
            self.player.pause()
            current_item = self.playlist_widget.currentItem()
            text = "Paused" if current_item is None else f"Paused: {current_item.text()}"
            self.set_now_playing(text)
            self.set_status("Playback paused")

        elif state == QMediaPlayer.PausedState:
            self.player.play()
            current_item = self.playlist_widget.currentItem()
            text = "Now Playing" if current_item is None else f"Now Playing: {current_item.text()}"
            self.set_now_playing(text)
            self.set_status("Playback resumed")

        else:
            self.play_selected_song()

    def stop_song(self):
        self.player.stop()
        self.set_now_playing("Now Playing: Stopped")
        self.set_status("Playback stopped")

    def play_next_song(self):
        total_items = self.playlist_widget.count()
        if total_items == 0:
            self.set_now_playing("Now Playing: Playlist is empty")
            self.set_status("Next unavailable: empty playlist")
            return

        current_row = self.playlist_widget.currentRow()

        if self.shuffle_enabled:
            next_row = self.get_random_row(exclude_row=current_row)
            if next_row is None:
                next_row = 0
        else:
            next_row = 0 if current_row == -1 else min(current_row + 1, total_items - 1)

        self.playlist_widget.setCurrentRow(next_row)
        self.play_selected_song()

    def play_previous_song(self):
        total_items = self.playlist_widget.count()
        if total_items == 0:
            self.set_now_playing("Now Playing: Playlist is empty")
            self.set_status("Previous unavailable: empty playlist")
            return

        current_row = self.playlist_widget.currentRow()

        if self.shuffle_enabled:
            prev_row = self.get_random_row(exclude_row=current_row)
            if prev_row is None:
                prev_row = 0
        else:
            prev_row = 0 if current_row == -1 else max(current_row - 1, 0)

        self.playlist_widget.setCurrentRow(prev_row)
        self.play_selected_song()

    def change_volume(self, value):
        self.audio_output.setVolume(value / 100.0)
        self.set_status(f"Volume: {value}%")

    def toggle_mute(self, muted):
        self.audio_output.setMuted(muted)
        self.set_status("Muted" if muted else "Unmuted")

    def change_playback_speed(self, speed):
        self.player.setPlaybackRate(float(speed))
        self.set_status(f"Speed: {speed:.1f}x")

    # ---------- Shuffle + Repeat ----------

    def toggle_shuffle(self):
        self.shuffle_enabled = not self.shuffle_enabled
        self.shuffle_button.setText("Shuffle: On" if self.shuffle_enabled else "Shuffle: Off")
        self.set_status("Shuffle enabled" if self.shuffle_enabled else "Shuffle disabled")

    def cycle_repeat_mode(self):
        if self.repeat_mode == "off":
            self.repeat_mode = "all"
        elif self.repeat_mode == "all":
            self.repeat_mode = "one"
        else:
            self.repeat_mode = "off"

        self._refresh_repeat_button_text()
        self.set_status(f"Repeat mode: {self.repeat_mode}")

    def get_random_row(self, exclude_row):
        total_items = self.playlist_widget.count()
        if total_items <= 1:
            return None
        choices = [i for i in range(total_items) if i != exclude_row]
        return random.choice(choices) if choices else None

    # ---------- Seek logic ----------

    def on_duration_changed(self, duration_ms):
        if duration_ms and duration_ms > 0:
            self.seek_supported_for_current_track = True
            self.seek_row_widget.show()
            self.seek_slider.setRange(0, duration_ms)
            self.total_time_label.setText(self.format_ms(duration_ms))
        else:
            self.seek_supported_for_current_track = False
            self.seek_row_widget.hide()
            self.seek_slider.setRange(0, 0)
            self.seek_slider.setValue(0)
            self.current_time_label.setText("00:00")
            self.total_time_label.setText("00:00")

    def on_position_changed(self, position_ms):
        if not self.seek_supported_for_current_track:
            return
        if not self.is_user_seeking:
            self.seek_slider.setValue(position_ms)
        self.current_time_label.setText(self.format_ms(position_ms))

    def on_seek_pressed(self):
        if self.seek_supported_for_current_track:
            self.is_user_seeking = True

    def on_seek_moved(self, position_ms):
        if self.seek_supported_for_current_track:
            self.current_time_label.setText(self.format_ms(position_ms))

    def on_seek_released(self):
        if not self.seek_supported_for_current_track:
            self.is_user_seeking = False
            return
        self.player.setPosition(self.seek_slider.value())
        self.is_user_seeking = False

    # ---------- End-of-track handling ----------

    def on_media_status_changed(self, status):
        if status != QMediaPlayer.EndOfMedia:
            return

        total_items = self.playlist_widget.count()
        if total_items == 0:
            self.set_now_playing("Now Playing: Playlist is empty")
            return

        current_row = self.playlist_widget.currentRow()

        if self.repeat_mode == "one":
            if current_row < 0:
                current_row = 0
                self.playlist_widget.setCurrentRow(current_row)
            self.player.setPosition(0)
            self.player.play()
            current_item = self.playlist_widget.currentItem()
            self.set_now_playing(
                f"Now Playing: {current_item.text()}" if current_item else "Now Playing"
            )
            self.set_status("Repeat one: restarted track")
            return

        if self.shuffle_enabled:
            next_row = self.get_random_row(exclude_row=current_row)
            if next_row is None:
                if self.repeat_mode == "all":
                    self.playlist_widget.setCurrentRow(0)
                    self.play_selected_song()
                else:
                    self.stop_song()
                    self.set_now_playing("Now Playing: End of playlist")
                return
            self.playlist_widget.setCurrentRow(next_row)
            self.play_selected_song()
            return

        if current_row < 0:
            self.stop_song()
            return

        next_row = current_row + 1
        if next_row < total_items:
            self.playlist_widget.setCurrentRow(next_row)
            self.play_selected_song()
        else:
            if self.repeat_mode == "all":
                self.playlist_widget.setCurrentRow(0)
                self.play_selected_song()
            else:
                self.stop_song()
                self.set_now_playing("Now Playing: End of playlist")
                self.set_status("Reached end of playlist")

    @staticmethod
    def format_ms(ms):
        total_seconds = max(0, ms // 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


def main():
    app = QApplication(sys.argv)

    # Setting these makes macOS show the correct app name in the menu
    # bar (otherwise it defaults to "Python") and gives QSettings a
    # consistent identity across platforms.
    app.setOrganizationName("ArkodeepApps")
    app.setApplicationName("Python Music Player")
    app.setApplicationDisplayName("Python Music Player")

    window = MusicPlayerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
