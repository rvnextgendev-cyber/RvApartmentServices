# Maintenance Agent Prototype

Streamlit UI that drives a small set of FastAPI microservices (payments, WhatsApp reminder stub, audit logger) plus a mock LLM. Everything runs locally via Docker Compose.

## Quickstart

```bash
docker compose up --build
```

Open http://localhost:8501 to use the UI.

## Service Topology

- `app`: Streamlit UI + agent logic; calls planner/explainer LLM and tool APIs.
- `payments-service`: FastAPI for flats and payment status (Postgres backed).
- `whatsapp-service`: FastAPI stub simulating WhatsApp reminder sending.
- `audit-service`: FastAPI to log actions to Postgres.
- `llm`: Mock FastAPI LLM that returns plans/explanations shaped like an Ollama chat response.
- `db`: Postgres seeded from `db/init.sql`.

Environment defaults live in `.env` (used by the Streamlit container).

## Data Model (Postgres)

- `flats(flat_id, flat_no, owner_name, phone_number, whatsapp_number)` unique on `flat_no`.
- `maintenance_payments(id, flat_id, month_year, is_paid, paid_on)`.
- `audit_logs(log_id, event_type, flat_id, month_year, details_json, created_at)`.

Seed data in `db/init.sql`: C-101 unpaid Dec 2025, B-302 paid Dec 2025, and two sample flats.

## Key Endpoints

Payments service:
- `GET /get_payment_status?flat_no={id}&month_year=YYYY-MM` → payment status.
- `POST /add_flat` → upsert a flat; body: `flat_no`, optional `owner_name`, `phone_number`, `whatsapp_number`.
- `GET /list_flats` → list flats.

WhatsApp service:
- `POST /send_reminder` → stub that returns a message id.

Audit service:
- `POST /log_event` → writes to `audit_logs`.

LLM mock:
- `POST /api/chat` → returns a human-readable message; in planner mode it includes the plan JSON in-line so the UI can still parse it.

## Agent Workflow (UI)

1) User enters a prompt (or picks a suggestion).  
2) UI calls planner LLM with a system prompt; it returns a plan JSON:  
   - `action`: `CHECK_ONLY` | `CHECK_AND_REMIND` | `ADD_FLAT`  
   - includes `flat_no`, `month_year`, and optional owner/phone/whatsapp for adds.  
3) UI executes tools based on the plan:  
   - `CHECK_ONLY`: call `payments-service/get_payment_status`.  
   - `CHECK_AND_REMIND`: same as above; if unpaid, call `whatsapp-service/send_reminder` and `audit-service/log_event`.  
   - `ADD_FLAT`: call `payments-service/add_flat` (upsert).  
4) UI calls explainer LLM with the JSON context to generate a user-facing explanation.  
5) UI shows the response plus debug JSON; input clears after each run.  
6) Manual flat form lets you add/update flats; “Refresh flat list” pulls `list_flats`.

## Environment (Streamlit)

```
PAYMENTS_URL=http://payments-service:8001
WHATSAPP_URL=http://whatsapp-service:8002
AUDIT_URL=http://audit-service:8003
LLM_URL=http://llm:11434
LLM_MODEL=llama3
```

## Typical Prompts

- "Add flat D-404 for Jane Doe, phone +911234567890."
- "Has B-302 paid for 2025-12?"
- "Check if C-101 has paid this month; if not, send WhatsApp."
- "Add flat E-202, owner John Smith, WhatsApp +910000000123."
