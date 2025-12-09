# Maintenance Agentic Demo – Project Documentation

This repository is a self-contained maintenance assistant that combines a Streamlit UI, several FastAPI microservices, a mock LLM, and a Postgres database. Everything is wired together with Docker Compose (for local use) and Kustomize (for Kubernetes-style deployment).

## Stack at a Glance
- Python + FastAPI + Uvicorn for the API services.
- Streamlit for the UI and agent orchestration.
- Postgres 16 with SQL seed data from `db/init.sql`.
- Docker / Docker Compose for local orchestration; ports are exposed for UI (8501) and DB (5433).
- FastMCP for an MCP server that exposes the same tools to MCP-capable clients.
- Kustomize manifests in `bridge/` for Kubernetes deployment (base + overlays/desktop).

## Services and Responsibilities
- `app` (Streamlit) – UI and agent flow; calls planner/explainer LLM endpoints plus the tool APIs.
  - Entrypoint: `app/streamlit_app.py`
  - External port: 8501
- `payments-service` (FastAPI) – flats CRUD-lite and payment status backed by Postgres.
  - Entrypoint: `services/payments_service.py`
  - Key endpoints: `/get_payment_status`, `/add_flat`, `/list_flats`
- `whatsapp-service` (FastAPI stub) – simulates sending WhatsApp reminders.
  - Entrypoint: `services/whatsapp_service.py`
  - Key endpoint: `/send_reminder`
- `audit-service` (FastAPI) – writes audit events to Postgres.
  - Entrypoint: `services/audit_service.py`
  - Key endpoint: `/log_event`
- `llm` (FastAPI mock) – acts like an Ollama chat endpoint for planner/explainer prompts.
  - Entrypoint: `services/llm_mock.py`
  - Endpoint: `/api/chat`
- `mcp` (FastMCP) – MCP tools that mirror the HTTP APIs and the mock LLM.
  - Entrypoint: `mcp_server.py`
  - Tools: `get_payment_status`, `add_flat`, `list_flats`, `send_whatsapp_reminder`, `log_event`, `check_and_remind`, `llm_chat`
- `db` (Postgres) – seeded with flats, payments, and audit tables from `db/init.sql`.

## Data Model (Postgres)
- `flats(flat_id, flat_no, owner_name, phone_number, whatsapp_number)` with a unique flat number.
- `maintenance_payments(id, flat_id, month_year, is_paid, paid_on)` for monthly payment status.
- `audit_logs(log_id, event_type, flat_id, month_year, details_json, created_at)` for recorded actions.
- Seed data: C-101 (unpaid Dec 2025) and B-302 (paid Dec 2025) plus two sample flats.

## Agent Workflow (UI)
1) User submits a prompt (or picks a suggestion).
2) The planner LLM (mock) returns a JSON plan with `action` (`CHECK_ONLY`, `CHECK_AND_REMIND`, `ADD_FLAT`), `flat_no`, and `month_year` (plus owner/contact when adding).
3) Tools execute based on the plan:
   - `CHECK_ONLY`: call `payments-service/get_payment_status`.
   - `CHECK_AND_REMIND`: same as above; if unpaid, call `whatsapp-service/send_reminder` and `audit-service/log_event`.
   - `ADD_FLAT`: upsert via `payments-service/add_flat`.
4) The explainer LLM (mock) turns the results into a user-facing explanation.
5) UI displays the explanation and debug JSON blocks (plan, payment, reminder, audit, flat result).
6) A manual form can add/update flats and list them on demand.

## Running Locally
- Prerequisites: Docker + Docker Compose.
- Start everything: `docker compose up --build`
- UI: http://localhost:8501
- Postgres: exposed on host 5433 (container 5432) for inspection.
- Environment defaults live in `.env` and are injected into `app` and `mcp` containers.

## Kubernetes (Kustomize) Notes
- Base manifests live in `bridge/base`; overlays (e.g., `bridge/overlays/desktop`) adjust services and PVC paths.
- Apply via `kubectl apply -k bridge/base` or an overlay such as `kubectl apply -k bridge/overlays/desktop`.
- Includes namespace creation, per-service deployments/services, and a network policy.

## Useful Files
- `docker-compose.yml` – service wiring, ports, and dependencies.
- `db/init.sql` – schema and seed data.
- `services/*.py` – FastAPI apps for payments, WhatsApp stub, audit, and mock LLM.
- `app/streamlit_app.py` – Streamlit UI and agent orchestration.
- `mcp_server.py` – MCP tool server for clients that speak the MCP protocol.
- `bridge/` – Kustomize manifests (base + overlays).

## Presentation Deck Reference
- Template: SlidesCarnival technology deck (editable in PowerPoint/Google Slides) – https://www.slidescarnival.com/technology-free-presentation-template/9295
- Suggested slide flow:
  1. Problem and scope.
  2. High-level architecture (service map + data flow).
  3. Stack overview (FastAPI, Streamlit, Postgres, Docker Compose, Kustomize, FastMCP).
  4. Agent workflow (planner → tools → explainer).
  5. Data model (tables and sample records).
  6. Deployment options (Compose vs. Kustomize).
  7. Demo steps (UI flow, key endpoints).
  8. Next steps / roadmap (real LLM swap, production WhatsApp/SMS, monitoring).

## Learning References (Stack)
- FastAPI: https://fastapi.tiangolo.com/
- Streamlit: https://docs.streamlit.io/
- Postgres: https://www.postgresql.org/docs/current/
- Docker Compose: https://docs.docker.com/compose/
- Kustomize: https://kubectl.docs.kubernetes.io/references/kustomize/
- FastMCP: https://github.com/promptfoo/fastmcp and https://pypi.org/project/fastmcp/
- Uvicorn: https://www.uvicorn.org/
- Requests: https://requests.readthedocs.io/en/latest/
- Pydantic: https://docs.pydantic.dev/latest/
