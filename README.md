# HarmonyPlayer Web

HarmonyPlayer Web is a Flask music player for music you own or are allowed to use. It provides authentication, uploads, playlists, a persistent HTML5 player, and user-specific settings.

## Features

- Register, login, logout
- Password hashing
- Protected user-specific library, playlists, and settings
- Secure audio uploads
- HTML5 audio playback
- Persistent queue
- Playlist management
- Client-side search, sort, and filter
- Dark mode by default with optional light mode
- Responsive layout for desktop, tablet, and mobile

## Screenshots

Add screenshots here after running the app.

## Requirements

- Python 3.11+ recommended
- Windows PowerShell

## Installation

### Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Configure environment variables

```powershell
Copy-Item .env.example .env
```

Set these values in `.env`:

- `SECRET_KEY`
- `DATABASE_URL`
- `UPLOAD_FOLDER`

## Database initialization

The SQLite database is created automatically on first start. No separate migration step is required for development.

## Running locally

```powershell
$env:FLASK_DEBUG = "1"
python app.py
```

Open `http://127.0.0.1:5000`.

## Uploading music

1. Sign in.
2. Open Library.
3. Upload MP3, WAV, OGG, FLAC, or M4A files.
4. Edit metadata fields when needed.

Uploaded files stay in the local `music/` directory and are only accessible to the owning user.

## Project structure

```text
HarmonyPlayer-Web/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
├── instance/
├── app/
├── templates/
├── static/
└── music/
```

## Security notes

- Passwords are hashed with Werkzeug.
- CSRF protection is enabled for state-changing requests.
- Uploaded filenames are sanitized.
- Path traversal is blocked.
- Only owners can access songs and playlists.
- Secrets come from environment variables.

## Deployment considerations

- Use a strong production `SECRET_KEY`.
- Store the database and uploads on durable storage.
- Prefer PostgreSQL for production scale.
- Put the app behind HTTPS and a reverse proxy.
- Consider moving `UPLOAD_FOLDER` outside the source tree.

## License

No license has been chosen yet.
