from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os

app = FastAPI(title="Payments Service")


def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "maintdb"),
        user=os.getenv("POSTGRES_USER", "maintuser"),
        password=os.getenv("POSTGRES_PASSWORD", "maintpass"),
        host=os.getenv("POSTGRES_HOST", "db"),
        port=5432,
    )


class FlatCreate(BaseModel):
    flat_no: str
    owner_name: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/get_payment_status")
def get_payment_status(flat_no: str, month_year: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT mp.is_paid, mp.paid_on
            FROM maintenance_payments mp
            JOIN flats f ON f.flat_id = mp.flat_id
            WHERE f.flat_no = %s AND mp.month_year = %s
            """,
            (flat_no, month_year),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No payment record found")

        is_paid, paid_on = row
        return {
            "flat_no": flat_no,
            "month_year": month_year,
            "is_paid": is_paid,
            "paid_on": paid_on.isoformat() if paid_on else None,
        }
    finally:
        conn.close()


@app.post("/add_flat")
def add_flat(flat: FlatCreate):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO flats (flat_no, owner_name, phone_number, whatsapp_number)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (flat_no) DO UPDATE SET
                owner_name = EXCLUDED.owner_name,
                phone_number = EXCLUDED.phone_number,
                whatsapp_number = EXCLUDED.whatsapp_number
            RETURNING flat_id
            """,
            (flat.flat_no, flat.owner_name, flat.phone_number, flat.whatsapp_number),
        )
        flat_id = cur.fetchone()[0]
        conn.commit()
        return {"status": "OK", "flat_id": flat_id, "flat_no": flat.flat_no}
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"DB error: {e.pgerror or str(e)}")
    finally:
        conn.close()


@app.get("/list_flats")
def list_flats():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT flat_no, owner_name, phone_number, whatsapp_number
            FROM flats
            ORDER BY flat_no
            """
        )
        rows = cur.fetchall()
        return [
            {
                "flat_no": r[0],
                "owner_name": r[1],
                "phone_number": r[2],
                "whatsapp_number": r[3],
            }
            for r in rows
        ]
    finally:
        conn.close()
