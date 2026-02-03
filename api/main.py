from fastapi import FastAPI, Request
from core.orchestrator import run

app = FastAPI(title="RCA Investigation Agent")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/webhook")
async def webhook(req: Request):
    payload = await req.json()
    return run(payload)