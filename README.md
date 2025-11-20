# Task Management REST API
**Django + DRF (Function-Based Views Only) + PostgreSQL (Async) + Redis + Celery + Docker + uv**

A production-grade, scalable, and containerized **Task Management REST API**, built with **Django REST Framework**, **function-based views**, **token authentication**, **PostgreSQL**, **Redis caching**, **Celery for background tasks**, **async CSV ingestion (1M+ records)**, and **email notifications**.

This project is optimized for **performance**, **scalability**, **security**, and **clean architecture**.

---

# Features

### **Authentication**
- Token-based Authentication (no Django sessions)
- User Registration + Login endpoints
- Token expiry & security best practices

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
- API to filter 1M+ records efficiently (uses PostgreSQL indexes + subqueries)

### **Caching & Performance**
- Redis caching for GET endpoints
- Cache invalidation strategies
- Async PostgreSQL connections
- Optimized QuerySets + subqueries for large data filtering
- Database monitoring using `pg_stat_statements`

### **Architecture & Tooling**
- Function-based views only (no CBVs or ViewSets)
- Clean project structure (separation of concerns)
- Environment-based configuration (dev/prod)
- uv for Python package and environment management
- Docker + docker-compose (Django, PostgreSQL, Redis, Celery worker)
- Git branching strategy with conventional commits
- Pre-commit hooks + linters + formatters
- Swagger / Postman API documentation
- Proper logging, error handling, and security hardening

---

# Project Structure
```
project/
│
├── src/
│   ├── config/
│   │   ├── settings/
│   │   ├── urls.py
│   │   └── celery.py
│   │
│   ├── users/
│   ├── tasks/
│   ├── common/
│   ├── email_service/
│   ├── celery_worker/
│   └── manage.py
│
├── docker/
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── README.md
└── .env.example
```

---

# Tech Stack
| Component | Technology |
|----------|------------|
| Backend | Django, Django REST Framework |
| Auth | Token Authentication |
| Database | PostgreSQL (async) |
| ORM | Django ORM |
| Cache | Redis |
| Background Tasks | Celery + Redis broker |
| Package Manager | uv |
| API Docs | Swagger / Postman |
| Containers | Docker + docker-compose |
| DB Versioning | Alembic |
| Linters | ruff / black |
| Rate Limiter | Django-ratelimit or custom middleware |

---

# Installation & Setup

## Clone the repository
```bash
git clone <repo_url>
cd project
```

## Environment variables
```bash
cp .env.example .env
```

## Create virtual environment using uv
```bash
uv venv --python 3.12
source .venv/bin/activate
```

## Install dependencies
```bash
uv sync
```

---

# Docker Setup

## Build and run everything:
```bash
docker compose up --build
```
Starts:
- Django API
- PostgreSQL
- Redis
- Celery Worker

---

# Authentication Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register/` | POST | Register user |
| `/api/auth/login/` | POST | Login & receive token |

---

# Task Endpoints
| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/tasks/` | GET | List tasks (cached) |
| `/api/tasks/` | POST | Create task |
| `/api/tasks/<id>/` | PUT | Update task |
| `/api/tasks/<id>/` | DELETE | Delete task |
| `/api/tasks/<id>/complete/` | POST | Mark complete → async email |

---

# CSV Processing Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/csv/upload/` | POST | Upload CSV (400MB) |
| `/api/csv/status/<task_id>/` | GET | Check Celery task status |
| `/api/records/filter/` | GET | Efficient filtering on 1M+ rows |

---
