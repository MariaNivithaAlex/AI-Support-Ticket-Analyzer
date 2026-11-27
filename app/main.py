from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .database import connect, init_db

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Support Ticket Desk",
    description="Classify support tickets by category, priority, and sentiment, then manage them through a REST API.",
    version="1.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class TicketCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=10000)
    category: str = Field(min_length=1, max_length=80)
    priority: Literal["Low", "Medium", "High", "Critical"]
    sentiment: Literal["Positive", "Neutral", "Negative"]


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["Open", "In Progress", "Resolved"] | None = None
    category: str | None = Field(default=None, min_length=1, max_length=80)
    priority: Literal["Low", "Medium", "High", "Critical"] | None = None
    sentiment: Literal["Positive", "Neutral", "Negative"] | None = None


def row_dict(row):
    return dict(row)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/tickets", status_code=201)
def create_ticket(ticket: TicketCreate):
    with connect() as db:
        cursor = db.execute(
            """INSERT INTO tickets (customer_name, email, subject, description, category, priority, sentiment, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticket.customer_name.strip(), str(ticket.email), ticket.subject.strip(), ticket.description.strip(),
             ticket.category.strip(), ticket.priority, ticket.sentiment, 1.0),
        )
        row = db.execute("SELECT * FROM tickets WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_dict(row)


@app.get("/api/tickets")
def list_tickets(
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    clauses, values = [], []
    for column, value in (("status", status), ("category", category), ("priority", priority)):
        if value:
            clauses.append(f"{column} = ?")
            values.append(value)
    if search:
        clauses.append("(subject LIKE ? OR description LIKE ? OR customer_name LIKE ? OR email LIKE ?)")
        values.extend([f"%{search}%"] * 4)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connect() as db:
        total = db.execute("SELECT COUNT(*) FROM tickets" + where, values).fetchone()[0]
        rows = db.execute(f"SELECT * FROM tickets{where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?", [*values, limit, offset]).fetchall()
    return {"items": [row_dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return row_dict(row)


@app.patch("/api/tickets/{ticket_id}")
def update_ticket(ticket_id: int, changes: TicketUpdate):
    fields = changes.model_dump(exclude_unset=True, exclude_none=True)
    if not fields:
        raise HTTPException(status_code=422, detail="Provide at least one field to update")
    fields["updated_at"] = "now"
    assignments = [f"{key} = ?" for key in fields if key != "updated_at"]
    values = [value for key, value in fields.items() if key != "updated_at"]
    assignments.append("updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')")
    with connect() as db:
        cursor = db.execute(f"UPDATE tickets SET {', '.join(assignments)} WHERE id = ?", [*values, ticket_id])
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ticket not found")
        row = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return row_dict(row)


@app.delete("/api/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int):
    with connect() as db:
        cursor = db.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")


@app.get("/api/stats")
def stats():
    with connect() as db:
        total = db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        open_count = db.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Open'").fetchone()[0]
        urgent = db.execute("SELECT COUNT(*) FROM tickets WHERE priority IN ('High', 'Critical') AND status != 'Resolved'").fetchone()[0]
        negative = db.execute("SELECT COUNT(*) FROM tickets WHERE sentiment = 'Negative'").fetchone()[0]
        categories = db.execute("SELECT category AS label, COUNT(*) AS count FROM tickets GROUP BY category ORDER BY count DESC").fetchall()
        priorities = db.execute("SELECT priority AS label, COUNT(*) AS count FROM tickets GROUP BY priority ORDER BY CASE priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END").fetchall()
        sentiments = db.execute("SELECT sentiment AS label, COUNT(*) AS count FROM tickets GROUP BY sentiment").fetchall()
        trend = db.execute("SELECT substr(created_at, 1, 10) AS date, COUNT(*) AS count FROM tickets WHERE created_at >= date('now', '-6 days') GROUP BY date ORDER BY date").fetchall()
    return {"total": total, "open": open_count, "urgent": urgent, "negative": negative,
            "categories": [row_dict(r) for r in categories], "priorities": [row_dict(r) for r in priorities],
            "sentiments": [row_dict(r) for r in sentiments], "trend": [row_dict(r) for r in trend]}
