"""
NetPulse backend API.

Receives scan results pushed FROM the local agent (one-way — this
backend never sends commands back down to the agent), compares them
against the stored baseline, calls Nemotron via Nebius Token Factory
to generate a plain-English explanation, and serves that to the
dashboard.
"""

import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="NetPulse backend")

TOKEN_FACTORY_API_KEY = os.getenv("TOKEN_FACTORY_API_KEY")

# TODO (week 4): replace this with real storage (even a JSON file or
# SQLite is fine to start) so the baseline survives a restart.
LAST_SCAN_BY_USER: dict[str, dict] = {}


class ScanPayload(BaseModel):
    subnet: str
    devices: list[dict]


def explain_with_nemotron(current: dict, previous: dict | None) -> str:
    """
    TODO (week 3): call Nemotron via Token Factory here.

    Rough shape (fill in once you've read the Token Factory API docs):

        response = requests.post(
            f"{TOKEN_FACTORY_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {TOKEN_FACTORY_API_KEY}"},
            json={
                "model": "nemotron-3-nano",  # or -super / -ultra depending on task
                "messages": [{"role": "user", "content": build_prompt(current, previous)}],
            },
        )

    Spend real time on the prompt: give it the current scan, the
    previous baseline, and ask specifically for (a) what's new or
    changed, (b) why it might matter, (c) one concrete next step.
    """
    raise NotImplementedError("wire this up in week 3")


@app.post("/scan")
def receive_scan(payload: ScanPayload, x_user_token: str = Header(...)):
    """
    The agent pushes results here. x_user_token authenticates which
    user/agent this is — never trust an unauthenticated payload.
    """
    # TODO (week 6): validate x_user_token against real user records
    if not x_user_token:
        raise HTTPException(status_code=401, detail="missing auth token")

    previous = LAST_SCAN_BY_USER.get(x_user_token)
    current = payload.model_dump()

    # explanation = explain_with_nemotron(current, previous)

    LAST_SCAN_BY_USER[x_user_token] = current

    return {"status": "received", "device_count": len(current["devices"])}


@app.get("/latest")
def latest_scan(x_user_token: str = Header(...)):
    """The dashboard calls this to display current status."""
    result = LAST_SCAN_BY_USER.get(x_user_token)
    if not result:
        raise HTTPException(status_code=404, detail="no scans yet")
    return result
