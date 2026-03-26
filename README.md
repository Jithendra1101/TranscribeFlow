# TranscribeFlow

A Flask web application that lets authenticated users upload audio files, automatically **transcribes** them using [OpenAI Whisper](https://github.com/openai/whisper), and generates an **AI-powered summary** using the [T5-base](https://huggingface.co/t5-base) model from Hugging Face Transformers — all from a clean browser UI or a REST API.

---

## Features

- **User Authentication** — Secure signup / login / logout backed by NeonDB (PostgreSQL) via Flask-SQLAlchemy and Flask-Login
- **Audio Transcription** — Converts speech to text using OpenAI Whisper (runs locally, no API key required)
- **Text Summarization** — Condenses the transcript with T5-base (Hugging Face), running fully on-device
- **Transcription History** — Every transcription and summary is saved to the cloud database and viewable in a paginated history page
- **Delete Records** — Users can permanently delete any past transcription from their history
- **Persistent Transcripts** — Each transcription is also saved as a `.txt` file in the `transcribes/` folder
- **REST API** — `POST /upload` endpoint for programmatic access
- **35 MB upload limit** — Handles typical audio files up to 35 MB

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask |
| Database / ORM | NeonDB (PostgreSQL) + Flask-SQLAlchemy |
| Auth | Flask-Login + Werkzeug |
| Transcription | OpenAI Whisper |
| Summarization | Hugging Face Transformers (T5-base) + PyTorch |
| Audio processing | FFmpeg (via `imageio-ffmpeg`) |
| Config | python-dotenv |

---

## Project Structure

```
TranscribeFlow/
├── app.py              # Flask app, routes, auth logic
├── transcribe.py       # Whisper-based audio transcription
├── summarize.py        # T5-base text summarization
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not committed)
├── templates/
│   ├── base.html       # Shared navbar/layout
│   ├── home.html       # Upload + live-record UI
│   ├── history.html    # Transcription history page
│   ├── login.html
│   └── signup.html
├── static/
│   └── style.css
├── upload/             # Temporary audio uploads
└── transcribes/        # Saved transcription .txt files
```

---

## Prerequisites

- Python 3.9 or later
- **FFmpeg** — required by Whisper for audio decoding

### Installing FFmpeg (Windows)

**Option A – Chocolatey (recommended):**
```powershell
choco install ffmpeg
```

**Option B – Manual:**
Download from [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/), extract, and add the `bin/` folder to your `PATH`.

> `imageio-ffmpeg` (included in `requirements.txt`) ships a bundled FFmpeg binary and is used automatically if a system FFmpeg is not found.

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Jithendra1101/TranscribeFlow/
cd TranscribeFlow
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `torch` and `transformers` are large packages. The first install may take several minutes. The T5-base model weights (~250 MB) are downloaded automatically on first run.

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
SQLALCHEMY_DATABASE_URI=postgresql://user:password@host/dbname?sslmode=require&channel_binding=require
```

> The app is configured for **NeonDB (PostgreSQL)**. Replace the URI with your own NeonDB connection string. psycopg2-binary is used as the driver (no separate ODBC install needed).

### 5. Run the application

```bash
python app.py
```

The app will be available at **http://127.0.0.1:5000**.

On first run, the SQLite database (`instance/users.db`) is created automatically.

---

## Usage

### Web UI

1. Navigate to `http://127.0.0.1:5000`
2. **Sign up** for an account, then **log in**
3. On the home page, click **Choose File** and select an audio file (MP3, WAV, M4A, etc.)
4. Click **Upload & Transcribe**
5. The transcript and AI-generated summary are displayed on the page and **saved to NeonDB**
6. Click **📂 History** in the navbar to browse all your past transcriptions and summaries
7. Expand any card to view the full text, copy, download, or delete the record

### REST API

**Endpoint:** `POST /upload`  
**Auth required:** Yes (session cookie from a browser login, or adapt for token auth)  
**Content-Type:** `multipart/form-data`  
**Field:** `audio` — the audio file

#### Example (curl)

```bash
curl -X POST http://127.0.0.1:5000/upload \
  -F "audio=@/path/to/your/audio.mp3" \
  -b "session=<your-session-cookie>"
```

#### Success response (`200 OK`)

```json
{
  "original_filename": "audio.mp3",
  "transcript_file": "audio.txt",
  "transcript": "Full transcribed text...",
  "summary": "Concise AI-generated summary..."
}
```

#### Error response

```json
{
  "error": "Description of what went wrong."
}
```

---

## Supported Audio Formats

Any format supported by FFmpeg, including: `mp3`, `wav`, `m4a`, `ogg`, `flac`, `aac`, `wma`, `webm`

---

## Models Used

| Task | Model | Size | Notes |
|---|---|---|---|
| Transcription | `openai/whisper-base` | ~140 MB | Loads lazily on first transcription |
| Summarization | `t5-base` | ~250 MB | Downloads from Hugging Face on first run |

Both models run **locally** — no external API calls or keys required after the initial download.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `default_secret_key` | Flask session signing key — change in production |
| `SQLALCHEMY_DATABASE_URI` | `sqlite:///users.db` | NeonDB (PostgreSQL) connection string |

---

## Known Limitations

- The in-memory result store (`_result_store`) is suitable for single-worker development only. For production, replace it with Redis or a database-backed store.
- Large audio files may take significant time to transcribe on CPU — consider a GPU for faster inference.
- The 35 MB upload limit can be adjusted via `MAX_CONTENT_LENGTH` in `app.py`.
