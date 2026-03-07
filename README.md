## Prototype Studio

Prototype Studio is a Django app for defining internal-tool specs and exporting runnable `Streamlit + SQLite` prototypes.

### What it does

- Create a project from a blank workspace or a seeded template.
- Define entities and typed fields.
- Define workflow states and prototype screens.
- Generate a shareable Streamlit package with `app.py`, `prototype_spec.json`, and a zip export.

### Quick start

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

### Demo bootstrap

If you want a seeded demo workspace immediately:

```bash
uv run python manage.py migrate
uv run python manage.py bootstrap_demo --generate
uv run python manage.py runserver
```

That creates:

- username: `demo`
- password: `demo-pass-123`
- project: `Field Ops Quote Builder`

### Run a generated prototype in the browser

After logging into the Django app, open a workspace and use:

- `Generate Streamlit package` to write the export files
- `Run prototype` to launch the generated app locally
- `Open prototype` to open the live Streamlit preview in a new tab

### Tests

```bash
uv run pytest
```
