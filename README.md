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

The database is **MongoDB** (not Mongoose—that is a Node.js ODM). You can browse the same cluster and database in **[MongoDB Compass](https://www.mongodb.com/products/compass)** using your **`MONGO_URI`** (and select **`MONGO_DB_NAME`** in the sidebar) to verify documents (`users`, `habits`, `habit_logs`, etc.) while the app or tests run.

### Passwords (demo / coursework)

User passwords are stored in MongoDB **as plain text** and compared with string equality on login (**no bcrypt** in this codebase). That keeps the project simple for local development and coursework; a real production service must use password hashing and other hardening.

### Optional: integration tests (real MongoDB)

With MongoDB running (for example **`docker compose up -d`** from the repo root), you can verify data is written and read from the database:

```bash
source .venv/bin/activate
export RUN_MONGO_INTEGRATION=1
pytest backend/tests/test_mongo_integration.py -v -rs
```

Append **`-rs`** so pytest prints **why** tests were skipped in the summary (plain **`-v`** hides skip reasons).

Uses **`MONGO_URI`** from your **`.env`** (pytest loads `.env` from the repo root before defaults, same as **`python run.py`**). Integration tests create a throwaway database named like **`mindtrack_int_<random>`**, then **drop** it—you will not see it long in Compass. Without **`RUN_MONGO_INTEGRATION=1`**, those tests are skipped so CI passes without Mongo.

If you set **`RUN_MONGO_INTEGRATION=1`** but pytest still reports **SKIPPED**, that means **nothing answered at **`MONGO_URI`** (often **connection refused** on **`localhost:27017`** when Mongo is not running). Fix by starting Mongo locally (**`docker compose up -d`** per [`.env.example`](.env.example)) or point **`MONGO_URI`** at **MongoDB Atlas** so the ping in the integration fixture succeeds.

Start MongoDB (when using local **`mongodb://localhost:27017`**), then run the app from the repository root. **Activate the virtual environment first** (same terminal session where you installed packages): if you see `ModuleNotFoundError: No module named 'fastapi'`, you skipped `pip install -r requirements.txt` or are not using the `.venv` Python.

```bash
source .venv/bin/activate   # macOS/Linux; Windows: .venv\\Scripts\\activate
python3 run.py
```

Open **http://127.0.0.1:5050/**, **http://127.0.0.1:5050/login**, or **http://127.0.0.1:5050/index.html** — all serve the **same** root **`index.html`** next to `run.py`, with the full login and register UI (no separate login template). Create an account on the **Register** tab, then you land on the dashboard. The default port is **5050** (not 5000) because on macOS **AirPlay Receiver** often binds port 5000; override with the `PORT` env var if needed.

### Troubleshooting

- **Quick API check (terminal)** — After **`python3 run.py`**, use the **port printed** in the banner (not necessarily **5050**). Run:

  ```bash
  curl -s "http://127.0.0.1:<port>/health"
  curl -s "http://127.0.0.1:<port>/mindtrack-http-port"
  ```

  The first should return **`{"status":"ok"}`** only when MongoDB is reachable and the app finished startup. The second returns the **listen port** for this request. If **`health`** fails or hangs, fix **`MONGO_URI` / `MONGO_DB_NAME`** (and TLS; see below) — **no browser change will fix a server that exits on startup.**

- **`pip install ...` → `Invalid requirement: '#'`** — Run **`pip install -r requirements.txt`** from the **MindTrack folder** (with `-r`). Do not pass a stray `#` as an argument. If you edited `requirements.txt`, each package must be on its own line; comment lines must start with `#` at the beginning of the line (see the sample file in the repo).
- **`[Errno 48] Address already in use`** — If you did **not** set `PORT`, `run.py` tries the first free port in **5050–5059** and prints the real URL. **Open the app at that URL** (UI and API on the same port). If the app moved to e.g. 5051 and you use **Live Server** for `index.html`, set the API base to that port (see [index.html](index.html) / `?api=...` in the README deployment section) or stop the process on 5050. If you **set** `PORT` and it is still taken, the process list from **`lsof`** is printed to stderr when possible.
- **MongoDB Atlas / TLS: `CERTIFICATE_VERIFY_FAILED` or `unable to get local issuer certificate`** — The app passes **certifi**’s CA bundle to PyMongo by default (`pip install -r requirements.txt` includes **certifi**). On macOS with a **python.org** build, also run **Install Certificates.command** from **Applications/Python 3.x**. If something on the network still breaks TLS (rare), you can set **`MONGO_TLS_INSECURE=1`** in `.env` **for local development only**—never in production.
- **Browser timeouts to `/api/...`** — If the server picked a port other than 5050, use the URL **printed in the terminal** for both the page and the API (or add **`?api=http://127.0.0.1:<port>`** once if the HTML is opened from another origin). **`GET /health`** on that same host/port should return **`{"status":"ok"}`** after Mongo connects. If requests still go to the wrong port (e.g. stuck on **:5050**), clear site **localStorage** key **`mindtrack_api_base`** or run **`localStorage.removeItem("mindtrack_api_base")`** once in the browser console (a previous **`?api=`** visit may have saved it).
- **Live Server / VS Code preview on another port** — The UI used to default API calls to **`127.0.0.1:5050`**. **`api.js`** probes **`/mindtrack-http-port`** (ports **5050–5059** and the same fallbacks as **`run.py`**) and saves **`mindtrack_api_base`** when it finds MindTrack. That endpoint returns the **port from your HTTP request**, so it stays correct even with **`uvicorn --reload`**. Probing targets **`127.0.0.1`** for IPv4 loopback. If the first try fails (e.g. the server was still starting), the next request probes again. You can still set **`window.MINDTRACK_DEV_API_PORT`**, **`<meta name="mindtrack-dev-api-port">`**, or **`?api=http://127.0.0.1:<port>`** (replace `<port>` with your API port) if needed.

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
- `password` (string, stored as plain text for this demo; not suitable for production)
- `created_at` (datetime)
- `last_login` (datetime or null)
- `preferences` (object): `reminder_time` (string), `theme` (string)

Example `users` document (field `password` is what the app writes; `password_hash` is still read for older or external examples, but the value is compared as plain text in this project):

```json
{
  "_id": { "$oid": "661f1a1a1a1a1a1a1a1a1a01" },
  "email": "juan.rojas@example.com",
  "full_name": "Juan Rojas",
  "password": "mySecretPass123",
  "created_at": { "$date": "2026-04-20T10:00:00.000Z" },
  "last_login": { "$date": "2026-04-21T09:00:00.000Z" },
  "preferences": { "reminder_time": "08:00", "theme": "light" }
}
```

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

Example `habit_logs` document (`user_id` / `habit_id` must match real documents in `users` and `habits`):

```json
{
  "_id": { "$oid": "662f2b2b2b2b2b2b2b2b2b02" },
  "user_id": { "$oid": "661f1a1a1a1a1a1a1a1a1a01" },
  "habit_id": { "$oid": "662e1c1c1c1c1c1c1c1c1c03" },
  "logged_at": { "$date": "2026-04-22T12:30:00.000Z" },
  "note": "Morning run",
  "streak_count": 5
}
```

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
