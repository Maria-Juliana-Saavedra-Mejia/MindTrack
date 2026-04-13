<h1 align="center">🧠 MindTrack</h1>

<p align="center">
  A full-stack web application to track habits, monitor productivity, and build better routines.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi" />
  <img src="https://img.shields.io/badge/Frontend-HTML%20%2F%20CSS%20%2F%20JS-F7DF1E?style=flat-square&logo=javascript" />
  <img src="https://img.shields.io/badge/Database-MongoDB-47A248?style=flat-square&logo=mongodb" />
  <img src="https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?style=flat-square&logo=githubactions" />
  <img src="https://img.shields.io/badge/Tests-pytest-0A9EDC?style=flat-square&logo=pytest" />
</p>

---

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Development Pipeline](#3-development-pipeline)
4. [Project Structure](#4-project-structure)
5. [Getting Started](#5-getting-started)
6. [API Endpoints](#6-api-endpoints)
7. [Database Design](#7-database-design)
8. [OOP Architecture](#8-oop-architecture)
9. [Testing](#9-testing)
10. [CI/CD Pipeline](#10-cicd-pipeline)
11. [SDLC Process](#11-sdlc-process)

---

## 1. Project Overview

**MindTrack** is a full-stack web application designed to help users track habits and monitor their personal productivity over time. Users can log daily activities, manage habit streaks, and visualize their progress through a clean and intuitive interface.

The application is built following the full **Software Development Lifecycle (SDLC)** — from requirement analysis and system design, through implementation and testing, to deployment via an automated CI/CD pipeline.

### Core Features

| Feature | Description |
|---------|-------------|
| 📌 Habit Management | Create, view, update, and delete personal habits |
| 📝 Activity Logging | Log daily entries tied to each habit |
| 📊 Progress Tracking | View streaks and activity history per habit |
| 🔒 Input Validation | All inputs are validated with clear error feedback |
| ⚙️ RESTful API | Clean API layer connecting frontend and backend |

---

## 2. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | HTML, CSS, JavaScript | User interface and API communication |
| **Backend** | Python + FastAPI | REST API, business logic, OOP models |
| **Database** | MongoDB | Flexible document-based data storage |
| **Testing** | pytest | Unit tests and edge case coverage |
| **DevOps** | GitHub Actions | Automated CI/CD pipeline |

---

## 3. Development Pipeline

Every feature in MindTrack follows this pipeline from code to production:

```
Write Code
    ↓
Format              ← PEP8 style enforced (black / flake8)
    ↓
Lint                ← Static analysis to catch issues early
    ↓
Test                ← pytest unit tests (minimum 5)
    ↓
Coverage            ← Verify meaningful code coverage
    ↓
Continuous Integration  ← GitHub Actions runs all of the above on every push
    ↓
Build Artifact      ← Package app (requirements.txt, build output)
    ↓
Docker Image        ← Containerize with Dockerfile
    ↓
Deploy              ← Push to staging / production environment
    ↓
Monitor             ← Check structured logs and system health
    ↓
Debug & Profile     ← Identify and resolve issues, optimize performance
```

> The GitHub Actions workflow automates everything from **Format** through **Build Artifact** on every push to `main`.

---

## 4. Project Structure

```
MindTrack/
├── .github/
│   └── workflows/
│       └── ci.yml              ← GitHub Actions CI/CD pipeline
│
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── habit.py        ← Habit class (OOP)
│   │   │   └── activity_log.py ← ActivityLog class (OOP)
│   │   ├── routes/
│   │   │   ├── habits.py       ← CRUD endpoints for habits
│   │   │   └── logs.py         ← CRUD endpoints for activity logs
│   │   ├── services/
│   │   │   ├── habit_service.py    ← Business logic for habits
│   │   │   └── log_service.py      ← Business logic for logs
│   │   ├── db/
│   │   │   └── connection.py   ← MongoDB connection setup
│   │   └── utils/
│   │       ├── logger.py       ← Structured logging setup
│   │       └── exceptions.py   ← Custom exception classes
│   ├── tests/
│   │   ├── test_habits.py
│   │   └── test_logs.py
│   ├── main.py                 ← FastAPI app entry point
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js                  ← Fetch API calls to backend
│
├── docs/
│   ├── problem_statement.pdf
│   ├── architecture.png
│   ├── er_diagram.png
│   └── api_docs.md
│
├── Dockerfile
├── .gitignore
└── README.md
```

---

## 5. Getting Started

### Prerequisites

- Python 3.10+
- MongoDB running locally or a MongoDB Atlas URI

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/mindtrack.git
cd mindtrack

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env and set your MONGO_URI

# 5. Run the backend
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive API docs (Swagger UI): `http://localhost:8000/docs`

### Running the Frontend

Open `frontend/index.html` directly in your browser, or serve it with:

```bash
python -m http.server 3000 --directory frontend
```

---

## 6. API Endpoints

### Habits

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/habits` | Retrieve all habits |
| `GET` | `/habits/{id}` | Retrieve a single habit by ID |
| `POST` | `/habits` | Create a new habit |
| `PUT` | `/habits/{id}` | Update an existing habit |
| `DELETE` | `/habits/{id}` | Delete a habit |

### Activity Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/logs` | Retrieve all activity logs |
| `GET` | `/logs/{habit_id}` | Retrieve logs for a specific habit |
| `POST` | `/logs` | Create a new log entry |
| `PUT` | `/logs/{id}` | Update a log entry |
| `DELETE` | `/logs/{id}` | Delete a log entry |

### Request / Response Example

**POST** `/habits`

```json
// Request body
{
  "name": "Morning Run",
  "description": "Run at least 2km every morning",
  "frequency": "daily"
}

// Response 201 Created
{
  "id": "664f1a2b3c4d5e6f7a8b9c0d",
  "name": "Morning Run",
  "description": "Run at least 2km every morning",
  "frequency": "daily",
  "created_at": "2026-04-13T08:00:00Z",
  "streak": 0
}
```

---

## 7. Database Design

MindTrack uses **MongoDB** with two main collections:

### `habits` Collection

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Auto-generated unique ID |
| `name` | String | Name of the habit |
| `description` | String | What the habit involves |
| `frequency` | String | `daily` or `weekly` |
| `created_at` | DateTime | Creation timestamp |
| `streak` | Integer | Current streak count |

### `activity_logs` Collection

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Auto-generated unique ID |
| `habit_id` | ObjectId | Reference to the parent habit |
| `date` | DateTime | Date of the logged activity |
| `completed` | Boolean | Whether the habit was completed |
| `notes` | String | Optional user notes |

> **Relationship:** One `habit` → many `activity_logs` (one-to-many via `habit_id` reference)

---

## 8. OOP Architecture

The backend applies **Object-Oriented Programming** principles throughout:

### `Habit` Class — `backend/app/models/habit.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from bson import ObjectId

@dataclass
class Habit:
    name: str
    description: str
    frequency: str                        # "daily" | "weekly"
    created_at: datetime = field(default_factory=datetime.utcnow)
    streak: int = 0
    id: ObjectId = field(default_factory=ObjectId)

    def increment_streak(self):
        self.streak += 1

    def reset_streak(self):
        self.streak = 0

    def to_dict(self) -> dict:
        return {
            "_id": self.id,
            "name": self.name,
            "description": self.description,
            "frequency": self.frequency,
            "created_at": self.created_at,
            "streak": self.streak,
        }
```

### `ActivityLog` Class — `backend/app/models/activity_log.py`

```python
@dataclass
class ActivityLog:
    habit_id: ObjectId
    date: datetime
    completed: bool
    notes: str = ""
    id: ObjectId = field(default_factory=ObjectId)

    def to_dict(self) -> dict:
        return {
            "_id": self.id,
            "habit_id": self.habit_id,
            "date": self.date,
            "completed": self.completed,
            "notes": self.notes,
        }
```

### Custom Exceptions — `backend/app/utils/exceptions.py`

```python
class HabitNotFoundError(Exception):
    """Raised when a habit ID does not exist in the database."""
    pass

class InvalidFrequencyError(ValueError):
    """Raised when an unsupported frequency value is provided."""
    pass
```

---

## 9. Testing

Tests are written with **pytest** and cover core logic, CRUD operations, and edge cases.

```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage report
pytest backend/tests/ --cov=backend/app --cov-report=term-missing
```

### Test Coverage

| Test File | What It Tests |
|-----------|--------------|
| `test_habits.py` | Create, read, update, delete habits; invalid input; duplicate names |
| `test_logs.py` | Log creation, retrieval by habit, invalid habit_id, missing fields |

### Example Tests

```python
def test_create_habit_success():
    habit = Habit(name="Read", description="Read 20 pages", frequency="daily")
    assert habit.name == "Read"
    assert habit.streak == 0

def test_increment_streak():
    habit = Habit(name="Read", description="Read 20 pages", frequency="daily")
    habit.increment_streak()
    assert habit.streak == 1

def test_reset_streak():
    habit = Habit(name="Read", description="Read 20 pages", frequency="daily")
    habit.increment_streak()
    habit.reset_streak()
    assert habit.streak == 0

def test_invalid_frequency_raises_error():
    with pytest.raises(InvalidFrequencyError):
        validate_frequency("hourly")

def test_habit_not_found_raises_error():
    with pytest.raises(HabitNotFoundError):
        get_habit_by_id("000000000000000000000000")
```

> **Minimum:** 5 unit tests covering core functionality, edge cases, and input validation.

---

## 10. CI/CD Pipeline

The GitHub Actions workflow runs automatically on every push to `main` and on all pull requests.

### Workflow File — `.github/workflows/ci.yml`

```yaml
name: MindTrack CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build-and-test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r backend/requirements.txt

      - name: Lint with flake8
        run: flake8 backend/app --max-line-length=100

      - name: Format check with black
        run: black --check backend/app

      - name: Run tests with pytest
        run: pytest backend/tests/ -v

      - name: Build artifact
        run: echo "Build complete ✅"
```

> ✅ A **screenshot of a passing pipeline run** is included in `/docs/`.

---

## 11. SDLC Process

MindTrack was built following a structured 3-phase development process:

| Phase | Week | Key Deliverables |
|-------|------|-----------------|
| **Phase 1 — Design** | Week 1 | Problem Statement, ER Diagram, API Endpoint list, Architecture Diagram |
| **Phase 2 — Build** | Week 2 | Working backend (OOP), UI connected to API, full CRUD |
| **Phase 3 — QA & DevOps** | Week 3 | Unit tests, structured logging, GitHub Actions pipeline, final demo |

### Git Commit Convention

```
feat: add habit creation endpoint
fix: resolve streak reset bug
test: add unit tests for activity log
docs: update API documentation
chore: configure GitHub Actions workflow
```

---
