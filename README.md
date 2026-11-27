# Support Ticket Desk

A full-stack support triage app built with FastAPI and SQLite. It assigns incoming tickets a category, priority, and tone, then provides ticket management APIs and a live dashboard.

## Features

- Manual category, priority, and sentiment assignment
- REST endpoints for creating, searching, filtering, updating, and deleting tickets
- SQLite persistence with no external database service
- Dashboard with volume, category, priority, sentiment, and status summaries
- Search and status/priority filters; update status or remove tickets from the table
- Interactive API documentation at `/docs`

## Run locally

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000> for the dashboard and <http://127.0.0.1:8000/docs> for the API docs. The database file `tickets.db` is created on first launch. Set `TICKET_DB_PATH` to use a different database path.

## API overview

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/tickets` | Create and automatically classify a ticket |
| `GET` | `/api/tickets` | List/filter/search tickets (`status`, `category`, `priority`, `search`, `limit`, `offset`) |
| `GET` | `/api/tickets/{id}` | Fetch one ticket |
| `PATCH` | `/api/tickets/{id}` | Update status, category, or priority |
| `DELETE` | `/api/tickets/{id}` | Delete one ticket |
| `GET` | `/api/stats` | Dashboard aggregates |

Example request:

```json
{
  "customer_name": "Jordan Lee",
  "email": "jordan@example.com",
  "subject": "Charged twice for my subscription",
  "description": "I was billed twice this month and need a refund. This is frustrating."
}
```

## Classifier notes

The starter classifier uses transparent keyword scoring so the app works immediately without model downloads or API keys. It is a useful demo baseline, not a substitute for a validated production model. Replace `app/classifier.py` with a model trained on representative, labeled tickets before relying on triage decisions operationally. Avoid sending sensitive ticket data to third-party model services without an appropriate privacy review.
