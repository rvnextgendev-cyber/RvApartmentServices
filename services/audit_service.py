from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os
import json

app = FastAPI(title="Audit Log Service")


def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "maintdb"),
        user=os.getenv("POSTGRES_USER", "maintuser"),
        password=os.getenv("POSTGRES_PASSWORD", "maintpass"),
        host=os.getenv("POSTGRES_HOST", "db"),
        port=5432,
    )


class AuditEvent(BaseModel):
    event_type: str
    flat_no: str
    month_year: str
    details: dict


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/log_event")
def log_event(ev: AuditEvent):
    conn = get_conn()
    try:
        cur = conn.cursor()
        # resolve flat_id
        cur.execute("SELECT flat_id FROM flats WHERE flat_no = %s", (ev.flat_no,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Flat not found")
        flat_id = row[0]

        cur.execute(
            """
            INSERT INTO audit_logs (event_type, flat_id, month_year, details_json)
            VALUES (%s, %s, %s, %s)
            RETURNING log_id
            """,
            (ev.event_type, flat_id, ev.month_year, json.dumps(ev.details)),
        )
        log_id = cur.fetchone()[0]
        conn.commit()
        return {"status": "OK", "log_id": log_id}
    finally:
        conn.close()
