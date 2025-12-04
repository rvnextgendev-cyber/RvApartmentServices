import json
import os
import time
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://payments-service:8001")
WHATSAPP_URL = os.getenv("WHATSAPP_URL", "http://whatsapp-service:8002")
AUDIT_URL = os.getenv("AUDIT_URL", "http://audit-service:8003")

LLM_URL = os.getenv("LLM_URL", "http://llm:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")


def llm_chat(system_prompt: str, user_prompt: str) -> str:
    """Call local Llama (Ollama-compatible) chat endpoint and return assistant text."""
    resp = requests.post(
        f"{LLM_URL}/api/chat",
        json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]


def tool_get_payment_status(flat_no: str, month_year: str) -> dict:
    resp = requests.get(
        f"{PAYMENTS_URL}/get_payment_status",
        params={"flat_no": flat_no, "month_year": month_year},
        timeout=5,
    )
    if resp.status_code == 404:
        return {"error": "not_found"}
    resp.raise_for_status()
    return resp.json()


def tool_send_whatsapp_reminder(flat_no: str, month_year: str) -> dict:
    resp = requests.post(
        f"{WHATSAPP_URL}/send_reminder",
        json={"flat_no": flat_no, "month_year": month_year},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()


def tool_log_event(event_type: str, flat_no: str, month_year: str, details: dict) -> dict:
    resp = requests.post(
        f"{AUDIT_URL}/log_event",
        json={
            "event_type": event_type,
            "flat_no": flat_no,
            "month_year": month_year,
            "details": details,
        },
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()


def tool_add_flat(flat_no: str, owner_name: str | None, phone_number: str | None, whatsapp_number: str | None) -> dict:
    resp = requests.post(
        f"{PAYMENTS_URL}/add_flat",
        json={
            "flat_no": flat_no,
            "owner_name": owner_name,
            "phone_number": phone_number,
            "whatsapp_number": whatsapp_number,
        },
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()


def tool_list_flats() -> list[dict]:
    resp = requests.get(f"{PAYMENTS_URL}/list_flats", timeout=5)
    resp.raise_for_status()
    return resp.json()


PLANNER_SYSTEM = """
You are MaintenancePlanner, an assistant that plans what to do for society maintenance.

You MUST output ONLY a single JSON object, nothing else.
No explanation, no backticks, no extra text.

The JSON format MUST be:
{
  "action": "CHECK_ONLY" or "CHECK_AND_REMIND" or "ADD_FLAT",
  "flat_no": "C-101",
  "month_year": "2025-12",
  "owner_name": "Optional when adding",
  "phone_number": "Optional when adding",
  "whatsapp_number": "Optional when adding"
}

- action:
  - "CHECK_ONLY": Just check payment status and report it.
  - "CHECK_AND_REMIND": Check status, and if unpaid, send a reminder and log it.
  - "ADD_FLAT": Create or update a flat record with owner and phone details.

If user does not specify month/year, assume current month-year (e.g., "2025-12") or pick a reasonable guess.
Try to extract flat number from text like "C-101", "B-302", etc.
If user wants to add a flat, include any provided owner/phone numbers; duplicates should be treated as updates.
"""

EXPLAINER_SYSTEM = """
You are MaintenanceExplainer.

Given:
- The original user request
- The payment status result
- Any actions taken (reminder sent, audit log)

Explain clearly in simple English what happened.
"""


def plan_action(user_message: str) -> dict:
    raw = llm_chat(PLANNER_SYSTEM, user_message)
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        json_str = raw[start : end + 1]
        return json.loads(json_str)
    except Exception as ex:
        return {"error": f"Failed to parse planner output: {ex}", "raw": raw}


def explain_result(
    user_message: str,
    plan: dict,
    payment: dict | None,
    reminder_result: dict | None,
    log_result: dict | None,
    flat_result: dict | None,
) -> str:
    context = {
        "user_message": user_message,
        "plan": plan,
        "payment_result": payment,
        "reminder_result": reminder_result,
        "log_result": log_result,
        "flat_result": flat_result,
    }
    user_prompt = (
        "Here is the context in JSON:\n\n"
        + json.dumps(context, indent=2)
        + "\n\nPlease explain to the user what you did in simple, concise language."
    )
    try:
        return llm_chat(EXPLAINER_SYSTEM, user_prompt)
    except Exception:
        # fallback: minimal human-readable line
        flat_no = plan.get("flat_no") or "the flat"
        month_year = plan.get("month_year") or "the requested month"
        if plan.get("action") == "ADD_FLAT":
            return f"Added or updated flat {flat_no}."
        if payment and payment.get("is_paid") is True:
            return f"{flat_no} has already paid for {month_year}."
        if payment and payment.get("is_paid") is False:
            return f"{flat_no} has not paid for {month_year} yet."
        return f"Checked payment status for {flat_no} for {month_year}."


st.set_page_config(page_title="Maintenance Agentic Demo", page_icon="MA")

st.title("Maintenance Agent (Local Docker Demo)")
st.write("Example: `Check if C-101 has paid for 2025-12. If not, send WhatsApp reminder.`")

# track input in session state so we can clear/reset
if "user_input" not in st.session_state:
    st.session_state["user_input"] = ""

suggestions = [
    "Add flat D-404 for Jane Doe, phone +911234567890.",
    "Has B-302 paid for 2025-12?",
    "Check if C-101 has paid this month; if not, send WhatsApp.",
    "Add flat E-202, owner John Smith, WhatsApp +910000000123.",
    "Add flat F-105 for Anita, WhatsApp +911112223334, then check payment.",
    "Check payment for D-404 for 2025-12; remind if unpaid.",
    "List the flats you have on file.",
    "Add flat A-110 for Rahul with phone +919876543210.",
]

col_s1, col_s2 = st.columns([3, 1])
with col_s1:
    suggested = st.selectbox(
        "Pick a suggested prompt (optional)",
        options=[""] + suggestions,
        index=0,
        key="suggested_prompt",
    )
with col_s2:
    if st.button("Use suggestion"):
        if suggested:
            st.session_state["user_input"] = suggested
        st.caption("Select a suggestion to populate the box.")
    else:
        st.caption("Select a suggestion to populate the box.")

user_input = st.text_input("Your message:", key="user_input")

ask_clicked = st.button("Ask Agent")
if ask_clicked and st.session_state["user_input"].strip():
    with st.spinner("Thinking..."):
        # small pause for a smoother perceived response/typing effect
        time.sleep(0.4)
        plan = plan_action(st.session_state["user_input"].strip())
        if "error" in plan:
            st.error(f"Planner error: {plan['error']}")
            st.code(plan.get("raw", ""), language="json")
        else:
            flat_no = plan.get("flat_no")
            month_year = plan.get("month_year")
            action = plan.get("action", "CHECK_ONLY")

            payment: dict | None = None
            reminder_result = None
            log_result = None
            add_flat_result = None

            if action == "ADD_FLAT":
                add_flat_result = tool_add_flat(
                    flat_no=flat_no,
                    owner_name=plan.get("owner_name"),
                    phone_number=plan.get("phone_number"),
                    whatsapp_number=plan.get("whatsapp_number"),
                )
            else:
                payment = tool_get_payment_status(flat_no, month_year)
                if (
                    action == "CHECK_AND_REMIND"
                    and isinstance(payment, dict)
                    and not payment.get("error")
                    and payment.get("is_paid") is False
                ):
                    reminder_result = tool_send_whatsapp_reminder(flat_no, month_year)
                    log_result = tool_log_event(
                        event_type="MAINTENANCE_REMINDER_SENT",
                        flat_no=flat_no,
                        month_year=month_year,
                        details={"reminder": reminder_result},
                    )

            explanation = explain_result(
                st.session_state["user_input"].strip(),
                plan,
                payment,
                reminder_result,
                log_result,
                add_flat_result,
            )

            st.markdown("### Agent Response")
            st.write(explanation)

            st.markdown("### Debug Info (Plan)")
            st.json(plan)
            if payment:
                st.markdown("### Debug Info (Payment)")
                st.json(payment)
            if reminder_result:
                st.markdown("### Debug Info (Reminder)")
                st.json(reminder_result)
            if log_result:
                st.markdown("### Debug Info (Audit Log)")
                st.json(log_result)
            if add_flat_result:
                st.markdown("### Debug Info (Flat)")
                st.json(add_flat_result)


st.markdown("---")
st.markdown("### Manage Flats Manually")
with st.form("manual_flat_form"):
    col1, col2 = st.columns(2)
    with col1:
        manual_flat_no = st.text_input("Flat number", value="D-404")
        manual_owner = st.text_input("Owner name", value="Owner Name")
    with col2:
        manual_phone = st.text_input("Phone number", value="+910000000099")
        manual_whatsapp = st.text_input("WhatsApp number", value="+910000000099")
    submitted = st.form_submit_button("Add / Update Flat")
    if submitted:
        try:
            result = tool_add_flat(
                flat_no=manual_flat_no,
                owner_name=manual_owner,
                phone_number=manual_phone,
                whatsapp_number=manual_whatsapp,
            )
            st.success(f"Saved flat {result.get('flat_no')} (id {result.get('flat_id')}).")
        except Exception as ex:
            st.error(f"Failed to add flat: {ex}")

if st.button("Refresh flat list"):
    try:
        flats = tool_list_flats()
        st.json(flats)
    except Exception as ex:
        st.error(f"Failed to load flats: {ex}")
