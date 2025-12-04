import json
import re
from datetime import datetime
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="LLM Mock", version="0.1.0")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]


def _detect_flat_no(text: str) -> str:
    match = re.search(r"\b[A-Z]-\d{3}\b", text.upper())
    return match.group(0) if match else "C-101"


def _detect_owner(text: str) -> str:
    match = re.search(r"(?:for|owner is)\s+([A-Za-z ]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip().title()
    return "New Owner"


def _detect_phone(text: str) -> str:
    match = re.search(r"(\+?\d{10,15})", text)
    return match.group(1) if match else "+910000000000"


def _detect_month_year(text: str) -> str:
    match = re.search(r"\b(20\d{2})[-/](0[1-9]|1[0-2])\b", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    now = datetime.utcnow()
    return f"{now.year}-{now.month:02d}"


def _should_remind(text: str) -> bool:
    return "remind" in text.lower() or "send" in text.lower()


def _build_plan(user_prompt: str) -> dict:
    if "add flat" in user_prompt.lower() or "create flat" in user_prompt.lower():
        phone = _detect_phone(user_prompt)
        return {
            "action": "ADD_FLAT",
            "flat_no": _detect_flat_no(user_prompt),
            "owner_name": _detect_owner(user_prompt),
            "phone_number": phone,
            "whatsapp_number": phone,
        }

    action = "CHECK_AND_REMIND" if _should_remind(user_prompt) else "CHECK_ONLY"
    return {
        "action": action,
        "flat_no": _detect_flat_no(user_prompt),
        "month_year": _detect_month_year(user_prompt),
    }


def _explain_from_context(user_prompt: str) -> str:
    try:
        start = user_prompt.find("{")
        end = user_prompt.rfind("}")
        ctx = json.loads(user_prompt[start : end + 1])
    except Exception:
        return "I parsed the request and responded with the available data."

    plan = ctx.get("plan", {}) or {}
    payment = ctx.get("payment_result", {}) or {}
    reminder = ctx.get("reminder_result") or {}
    flat_result = ctx.get("flat_result") or {}
    log_result = ctx.get("log_result") or {}

    flat_no = plan.get("flat_no", "the flat")
    month_year = plan.get("month_year", "the requested month")

    if payment.get("error") == "not_found":
        status_line = f"I could not find payment data for {flat_no} for {month_year}."
    elif payment.get("is_paid") is True:
        paid_on = payment.get("paid_on")
        status_line = f"{flat_no} has already paid for {month_year}" + (f" on {paid_on}." if paid_on else ".")
    elif payment.get("is_paid") is False:
        status_line = f"{flat_no} has not paid for {month_year} yet."
    elif flat_result:
        status_line = f"Added or updated flat {flat_result.get('flat_no', flat_no)} with owner info."
    else:
        status_line = f"I checked payment status for {flat_no} for {month_year}."

    reminder_line = ""
    if reminder:
        reminder_line = f" Sent a WhatsApp reminder at {reminder.get('sent_at')}."
    audit_line = ""
    if log_result:
        audit_line = f" Logged the action with id {log_result.get('log_id')}."

    return status_line + reminder_line + audit_line


@app.post("/api/chat")
def chat(req: ChatRequest):
    system_prompt = req.messages[0].content if req.messages else ""
    user_prompt = req.messages[-1].content if req.messages else ""

    if "MaintenancePlanner" in system_prompt:
        plan = _build_plan(user_prompt)
        content = f"I'll handle it. Here's the plan: {json.dumps(plan)}"
    else:
        content = _explain_from_context(user_prompt)

    return {
        "message": {"role": "assistant", "content": content},
        "done": True,
    }
