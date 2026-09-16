# HarmonyPlayer
A modern offline music player built with Python and PySide6.
## Features
- Open local audio files (`.mp3`, `.wav`, `.flac`, `.ogg`, `.m4a`)
- Playlist with duplicate prevention
- Drag & drop files into playlist
- Double-click to play
- Play / Pause / Stop / Next / Previous
- Shuffle + Repeat (`Off`, `All`, `One`)
- Conditional seek bar (auto-hides when seek unsupported)
- Save/Load playlist as `.m3u`
- Remove selected tracks
- Volume + Mute + Playback Speed (0.5x to 2.0x)
- Keyboard shortcuts
- Light/Dark theme toggle
- Persistent settings via `QSettings`
- Native menu integration on macOS (About/Quit relocated into the app menu)
## Keyboard Shortcuts
- `Space` → Play/Pause
- `Ctrl + Right` (`Cmd + Right` on macOS) → Next track
- `Ctrl + Left` (`Cmd + Left` on macOS) → Previous track
- `Delete` → Remove selected track(s)
- `Ctrl + M` (`Cmd + M` on macOS) → Mute/Unmute
- `Ctrl + T` (`Cmd + T` on macOS) → Toggle theme
- `Ctrl + Q` (`Cmd + Q` on macOS) → Quit
## Install
```bash
pip install PySide6
```

### Linux audio codec support
`pip install PySide6` alone may not be enough for MP3/FLAC/OGG playback on Linux. Install the GStreamer plugins your distro needs, e.g. on Debian/Ubuntu:
```bash
sudo apt install gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav
```

### macOS notes
Playback uses the native AVFoundation backend. MP3/M4A/WAV are well supported; FLAC/OGG support can vary by macOS/Qt version, so test those formats after install.
## Run
```bash
python main.py
```
## Notes
- Seek bar is shown only when the current media backend reports valid duration/seek support.
- On some systems/codecs (commonly some FLAC setups), seeking may be unavailable; UI handles this gracefully.
- The file dialog defaults to your platform's Music folder (`~/Music` on macOS/Linux).
