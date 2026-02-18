# Cardplay

A card game management application.

## Setup

```bash
# Install dependencies
uv sync

# Run migrations
PYTHONPATH=. DJANGO_SETTINGS_MODULE=settings uv run django-admin migrate

# Create a superuser (optional, for admin access)
PYTHONPATH=. DJANGO_SETTINGS_MODULE=settings uv run django-admin createsuperuser
```

## Running the app

```bash
uv run python app.py
```

The app will be available at http://localhost:8001

- Alive UI: http://localhost:8001/alive/
- Django Admin: http://localhost:8001/admin/
