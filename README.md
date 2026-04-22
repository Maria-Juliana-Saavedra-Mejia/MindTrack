# MindTrack

MindTrack is a habit-tracking web app for students and young professionals. You register once, sign in with email and password, then manage habits, log completions, see streaks and charts on the dashboard, review a month calendar of activity, and optionally generate short AI coach notes from your recent data.

## Quick start

You need **Python 3.11+**, **MongoDB** reachable from your machine, and a virtual environment.

```bash
cd MindTrack
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Where is `.env`?

Create the file **`.env` in the project root** — the same directory as `run.py`, `index.html`, and `requirements.txt` (not inside `backend/` or `frontend/`). Copy from [`.env.example`](.env.example) and edit the values below.

### What to put in `.env`

Edit `.env` and set only these two values:

- `MONGO_URI` — connection string to your MongoDB cluster or host. Examples: `mongodb://localhost:27017` for local Mongo, or **`mongodb+srv://user:password@cluster...mongodb.net/`** for MongoDB Atlas. You may include or omit a trailing slash; the app strips trailing slashes before connecting. Put the **database name only** in `MONGO_DB_NAME`, not in the URI path, unless your provider requires otherwise (this project uses `MONGO_DB_NAME` as the database selector).
- `MONGO_DB_NAME` — the logical database name, e.g. `mindtrack_db`.

Start MongoDB, then run the app from the repository root:

```bash
python run.py
```

Open **http://127.0.0.1:5000/**, **http://127.0.0.1:5000/login**, or **http://127.0.0.1:5000/index.html** — all serve the **same** root **`index.html`** next to `run.py`, with the full login and register UI (no separate login template). Create an account on the **Register** tab, then you land on the dashboard.

## Using the app

- **Login** — Email, password, optional “Remember me” (token is stored in the browser; use a private device).
- **Dashboard** — Active habits count, today’s completions, longest streak, a 30-day completion chart, AI insight card with refresh, and quick one-tap logging for today’s habits.
- **Habits** — List of habit cards (category, color, streak). Use **+** to open the side drawer and create a habit (frequency, category, color, emoji). Edit or delete from each card.
- **Log** — Month grid: dots show which habits you completed on a day; click a day to see entries and delete if needed.
- **Logout** — Clears the session token in the browser and returns you to login.

## Project layout

```
MindTrack/
├── index.html               # Static entry; also served at http://.../index.html
├── backend/
│   ├── app/                 # Flask package (config, models, routes, services, utils)
│   └── tests/               # pytest suite
├── frontend/
│   ├── static/              # CSS and JavaScript (served at /static/...)
│   └── templates/           # Jinja pages (dashboard, habits, log)
├── .github/workflows/       # CI (flake8 + pytest + coverage)
├── run.py                   # Entry point (adds backend/ to Python path)
├── requirements.txt
├── .env                     # You create this (gitignored); see "Where is .env" above
└── .env.example             # Mongo URI + database name only
```

The Flask server serves the REST API under `/api/...` and dashboard pages from **`frontend/templates/`**. The **entry/login experience** lives only in the repo-root **`index.html`**. Static assets (CSS/JS) are under **`frontend/static/`** and are exposed at **`/static/...`** URLs.

## MongoDB data model (expected collections)

The app uses the database named in `MONGO_DB_NAME`. Collections are created on first write; indexes are ensured on startup.

**`users`**

- `_id` (ObjectId)
- `full_name` (string)
- `email` (string, unique index)
- `password_hash` (string, bcrypt)
- `created_at` (datetime)
- `last_login` (datetime or null)
- `preferences` (object): `reminder_time` (string), `theme` (string)

**`habits`**

- `_id` (ObjectId)
- `user_id` (ObjectId, ref users)
- `name`, `description` (string)
- `frequency`: `"daily"` or `"weekly"`
- `category`: `"health"` | `"productivity"` | `"mindfulness"` | `"other"`
- `color` (hex string), `icon` (emoji string)
- `created_at` (datetime)
- `is_active` (bool)

**`habit_logs`**

- `_id` (ObjectId)
- `habit_id` (ObjectId, ref habits)
- `user_id` (ObjectId, ref users)
- `logged_at` (datetime, UTC)
- `note` (string, optional)
- `streak_count` (int, snapshot when logged)

**`ai_insights`**

- `_id` (ObjectId)
- `user_id` (ObjectId)
- `generated_at` (datetime)
- `insight_type` (string, e.g. `suggestion`)
- `compliment`, `observation`, `tip` (strings)
- `content` (string, optional JSON string duplicate of the three fields)
- `habits_analyzed` (array of ObjectId)

## Configuration and security

The **`.env` file is only for MongoDB**: `MONGO_URI` and `MONGO_DB_NAME`.

JWT signing and OpenAI are **not** read from `.env` by default. For local development, the app uses built-in placeholder defaults so you can run immediately. **Before production**, set real values in your hosting provider’s environment (for example `JWT_SECRET` and `OPENAI_API_KEY`). Use a long random `JWT_SECRET` and a valid OpenAI API key if you want working AI insights.

## API (short overview)

| Area        | Examples |
|------------|----------|
| Auth       | `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| Habits     | `GET/POST /api/habits`, `GET/PUT/DELETE /api/habits/<id>` |
| Logs       | `GET/POST /api/logs`, `DELETE /api/logs/<id>`, streak and summary endpoints under `/api/logs/...` |
| AI         | `GET /api/ai/insights`, `POST /api/ai/generate` |

All protected routes expect `Authorization: Bearer <token>` (token returned on login/register).

## Development

```bash
source .venv/bin/activate
flake8 backend/app backend/tests --max-line-length=100 --extend-ignore=E501
pytest -v --cov=app --cov-report=term-missing --cov-fail-under=70
```

CI runs the same checks on pushes and pull requests to `main` (see `.github/workflows/ci.yml`).

## Health check

`GET /health` returns `{"status": "ok"}` when the app process is up.
