# Task Management REST API
**Django + DRF (Function-Based Views Only) + PostgreSQL (psycopg2) + Redis + Celery + Docker + uv**

A production-grade, scalable, and containerized **Task Management REST API**, built with **Django REST Framework**, **function-based views**, **token authentication**, **PostgreSQL**, **Redis caching**, **Celery for background tasks**, **async CSV ingestion (1M+ records)**, and **email notifications**.

This project is optimized for **performance**, **scalability**, **security**, and **clean architecture**.

---

# Features

### **Authentication**
- Token-based Authentication (no Django sessions)
- User Registration + Login endpoints
- Sends an email notification after user registration

### **Tasks Module**
- Create / View / Update / Delete tasks
- Mark task as complete
- Sends an email notification asynchronously when a task is completed

### **CSV Processing (Heavy Load)**
- Upload **~400MB CSV file**
- File is validated before processing
- Celery worker parses CSV **asynchronously**
- Bulk insert into **PostgreSQL** using async Django ORM
- Handles **1 million+ records**
- API to check CSV processing status
- API to filter 1M+ records efficiently

### **Caching & Performance**
- Redis caching for GET endpoints
- Cache invalidation strategies
- Async PostgreSQL connections
- Optimized QuerySets for large data filtering

### **Architecture & Tooling**
- Function-based views only
- uv for Python package and environment management
- Docker + docker-compose (Django, PostgreSQL, Redis, Celery worker)
- Git branching strategy with conventional commits
- Pre-commit hooks + linters + formatters
- Swagger API documentation
- Logging and error handling

---

### High-level components

- `users/` — user registration, authentication, and email tasks
- `tasks/` — task management API (create/list/update/delete, complete)
- `csv_processor/` — models, views, Celery tasks, pagination, and serializers for CSV ingestion and querying
- `config/` — Django settings, Celery app, and ASGI/WGI
- `utils/` — helper utilities such as caching helpers
- `scripts/` — scripts for application entrypoint

---

## Quickstart (Docker)

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Build and start services:

```bash
docker compose up --build -d
```

3. Apply migrations and create a superuser:

```bash
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser
```

Notes
- Change `.env` values to match your infrastructure (Postgres / Redis / SMTP).

---

## Local development (non-Docker)

1. Create and activate a virtualenv, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

2. Copy and edit `.env` with DB and Redis details:

```bash
cp .env.example .env
```

3. Run migrations and the server:

```bash
python manage.py migrate
python manage.py runserver
```

4. Start a local Celery worker (ensure Redis is running):

```bash
celery -A config.celery worker --loglevel=info
```

---

## Configuration

Place secrets in environment variables. Key settings found in `config/settings.py` include:

- `DATABASE_URL` — Postgres connection string
- `REDIS_URL` — Redis for cache and Celery broker
- `EMAIL_*` settings — SMTP host, port, user, password
- `DEFAULT_CACHE_TTL` — default TTL (in seconds) used by caching helpers

---

## Key endpoints (summary)

Authentication
- `POST /api/v1/auth/user/register/` — register a user
- `POST /api/v1/auth/user/login/` — login and receive token
- `GET /api/v1/auth/user/me/` — get currently logged in user
- `POST /api/v1/auth/user/logout/` — revoke token and logout user

Tasks
- `GET /api/v1/tasks/` — list tasks (supports caching + pagination)
- `POST /api/v1/tasks/` — create
- `PUT /api/v1/tasks/<id>/` — update
- `DELETE /api/v1/tasks/<id>/` — delete
- `POST /api/v1/tasks/<id>/complete/` — mark complete & enque completion emails

Health-Check
- `GET /api/v1/health-check/` — services health check (db + celery + redis)

CSV Processing
- `POST /api/v1/csv-data/uploads/` — upload CSV
- `GET /api/v1/csv-data/uploads/` — list uploads
- `GET /api/v1/csv-data/uploads/<upload_id>/` — details + status
- `GET /api/v1/csv-data/uploads/<upload_id>/progress/` — progress
- `GET /api/v1/csv-data/uploads/<upload_id>/data/` — rows listing with filtering & pagination
- `DELETE /api/v1/csv-data/uploads/<upload_id>/delete/` - deletes csv record from database and media folder

For exact query-string parameters (search, filters, columns, sort_by, page, page_size, nocache) see `csv_processor/views.py` and `csv_processor/pagination.py`.

---

## CSV pipeline (how it works)

1. File is uploaded and saved in `media/csv_uploads/` and a `CSVUpload` record is created.
2. A Celery task is enqueued with the upload ID.
3. The worker reads the CSV in chunks (pandas), normalizes header names to snake_case, converts rows to dictionaries, and bulk-inserts them into `CSVData.data` (JSONField) in batches.
4. Progress is written to `CSVUpload.processed_rows`; key metadata and page snapshots may be cached.
5. On completion, an email is sent to the uploader with processing statistics.

Design notes
- Dynamic JSON storage makes the system flexible for arbitrary CSV schemas
- Header normalization ensures consistent keys; the original header-to-key mapping can be persisted to `CSVUpload.metadata` if you want to preserve raw names.

---

## Caching & pagination

- The `utils/cache.py` module provides request-aware response caching (per-user + path + query) and generic key/value helpers for the CSV pagination and counts.
- `csv_processor/pagination.py` contains three pagination styles: page-based, streaming, and cursor-based, designed for large datasets. Page responses and counts are cached for short TTLs for performance.

---
