from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="WhatsApp Service (Stub)")


class ReminderRequest(BaseModel):
    flat_no: str
    month_year: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/send_reminder")
def send_reminder(req: ReminderRequest):
    # Stub: just simulate sending WhatsApp
    message_id = f"local-whatsapp-{int(datetime.utcnow().timestamp())}"
    print(
        f"[STUB] Sending WhatsApp reminder for flat {req.flat_no} "
        f"for {req.month_year}, message_id={message_id}"
    )
    return {
        "status": "SENT",
        "message_id": message_id,
        "flat_no": req.flat_no,
        "month_year": req.month_year,
    }
