<div align="center">

# Prototype Studio

**Define business-tool specs visually. Export runnable Streamlit prototypes instantly.**

[![CI](https://github.com/pradhankukiran/prototype-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/pradhankukiran/prototype-studio/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Django 6.0](https://img.shields.io/badge/django-6.0-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Streamlit](https://img.shields.io/badge/streamlit-exports-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Railway](https://img.shields.io/badge/deploy-Railway-0B0D0E?logo=railway&logoColor=white)](https://railway.app)

</div>

---

Prototype Studio is a Django-powered web app that lets you design internal business tools — define entities, fields, workflows, and screens — then generate fully functional **Streamlit + SQLite** prototypes you can run, share, or export as a zip.

## Features

- **Visual Spec Builder** — Create projects from scratch or jump-start with built-in templates (Quote Builder, CRM, Approval Workflow, Case Tracker)
- **Entity & Field Designer** — Define data models with typed fields and configure relationships
- **Workflow Engine** — Set up workflow states and transitions for your business processes
- **Screen Designer** — Design prototype screens with a visual editor
- **One-Click Generation** — Export complete Streamlit apps with `app.py`, `prototype_spec.json`, and all dependencies
- **Live Preview** — Run and preview generated prototypes directly in the browser
- **Zip Export** — Download shareable packages ready to deploy anywhere

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0, Gunicorn, WhiteNoise |
| Prototype Runtime | Streamlit, SQLite |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Package Manager | uv |
| Linting & Formatting | Ruff |
| Testing | pytest, pytest-django |
| CI/CD | GitHub Actions |
| Containerization | Docker, Docker Compose |
| Deployment | Railway |

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# Clone the repository
git clone https://github.com/pradhankukiran/prototype-studio.git
cd prototype-studio

# Install dependencies
uv sync

# Run migrations and create a superuser
uv run python manage.py migrate
uv run python manage.py createsuperuser

# Start the dev server
uv run python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) and start building.

### Demo Mode

Spin up a pre-seeded workspace instantly:

```bash
uv run python manage.py migrate
uv run python manage.py bootstrap_demo --generate
uv run python manage.py runserver
```

This creates a demo account (`demo` / `demo-pass-123`) with a **Field Ops Quote Builder** project ready to explore.

### Docker

```bash
docker compose up
```

## Usage

1. **Create a project** — Start from a blank workspace or pick a template
2. **Define your spec** — Add entities, fields, workflow states, and screens
3. **Generate** — Click "Generate Streamlit package" to build the prototype
4. **Preview** — Hit "Run prototype" to launch it, then "Open prototype" to view it live
5. **Export** — Download the zip package to share or deploy independently

## Running Tests

```bash
uv run pytest
```

## Project Structure

```
prototype-studio/
├── builder/              # Main Django app
│   ├── models.py         # Project, Entity, Field, Workflow models
│   ├── views.py          # Web views and API endpoints
│   ├── services/         # Code generation & runtime engine
│   └── templates/        # Django HTML templates
├── config/               # Django settings (dev / production)
├── generated/            # Output directory for generated prototypes
├── docs/                 # Documentation
├── pyproject.toml        # Dependencies & project metadata
├── Dockerfile            # Multi-stage production build
├── docker-compose.yml    # Local dev with PostgreSQL
└── railway.json          # Railway deployment config
```
