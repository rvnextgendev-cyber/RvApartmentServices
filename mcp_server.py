import os
from datetime import datetime
import requests
from fastmcp import FastMCP

PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://payments-service:8001")
WHATSAPP_URL = os.getenv("WHATSAPP_URL", "http://whatsapp-service:8002")
AUDIT_URL = os.getenv("AUDIT_URL", "http://audit-service:8003")
LLM_URL = os.getenv("LLM_URL", "http://llm:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")

mcp = FastMCP("maintenance-services")


@mcp.tool()
def get_payment_status(flat_no: str, month_year: str):
    """Fetch payment status for a flat/month."""
    resp = requests.get(
        f"{PAYMENTS_URL}/get_payment_status",
        params={"flat_no": flat_no, "month_year": month_year},
        timeout=10,
    )
    if resp.status_code == 404:
        return {"error": "not_found", "flat_no": flat_no, "month_year": month_year}
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def add_flat(flat_no: str, owner_name: str | None = None, phone_number: str | None = None, whatsapp_number: str | None = None):
    """Add or update a flat record."""
    resp = requests.post(
        f"{PAYMENTS_URL}/add_flat",
        json={
            "flat_no": flat_no,
            "owner_name": owner_name,
            "phone_number": phone_number,
            "whatsapp_number": whatsapp_number,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def list_flats():
    """List known flats."""
    resp = requests.get(f"{PAYMENTS_URL}/list_flats", timeout=10)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def send_whatsapp_reminder(flat_no: str, month_year: str):
    """Send a WhatsApp reminder (stub)."""
    resp = requests.post(
        f"{WHATSAPP_URL}/send_reminder",
        json={"flat_no": flat_no, "month_year": month_year},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    data["sent_at"] = datetime.utcnow().isoformat()
    return data


@mcp.tool()
def log_event(event_type: str, flat_no: str, month_year: str, details: dict | None = None):
    """Log an audit event."""
    resp = requests.post(
        f"{AUDIT_URL}/log_event",
        json={
            "event_type": event_type,
            "flat_no": flat_no,
            "month_year": month_year,
            "details": details or {},
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def check_and_remind(flat_no: str, month_year: str):
    """
    Check payment status and, if unpaid, send a reminder and log it.
    Returns a summary with payment, reminder, and audit results.
    """
    result: dict = {"flat_no": flat_no, "month_year": month_year}

    # Check payment status
    pay_resp = requests.get(
        f"{PAYMENTS_URL}/get_payment_status",
        params={"flat_no": flat_no, "month_year": month_year},
        timeout=10,
    )
    if pay_resp.status_code == 404:
        result["payment"] = {"error": "not_found"}
        return result
    pay_resp.raise_for_status()
    payment = pay_resp.json()
    result["payment"] = payment

    # If already paid, no reminder
    if payment.get("is_paid"):
        return result

    # Send reminder
    rem_resp = requests.post(
        f"{WHATSAPP_URL}/send_reminder",
        json={"flat_no": flat_no, "month_year": month_year},
        timeout=10,
    )
    rem_resp.raise_for_status()
    reminder = rem_resp.json()
    reminder["sent_at"] = datetime.utcnow().isoformat()
    result["reminder"] = reminder

    # Log audit
    audit_resp = requests.post(
        f"{AUDIT_URL}/log_event",
        json={
            "event_type": "MAINTENANCE_REMINDER_SENT",
            "flat_no": flat_no,
            "month_year": month_year,
            "details": {"reminder": reminder},
        },
        timeout=10,
    )
    audit_resp.raise_for_status()
    result["audit_log"] = audit_resp.json()

    return result


@mcp.tool()
def llm_chat(user_message: str):
    """Pass through to the mock LLM for explanations/plans."""
    resp = requests.post(
        f"{LLM_URL}/api/chat",
        json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful maintenance assistant."},
                {"role": "user", "content": user_message},
            ],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    mcp.run()
