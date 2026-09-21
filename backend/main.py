"""
NetPulse backend API.

Receives scan results pushed FROM the local agent (one-way — this
backend never sends commands back down to the agent), diffs the scan
against the stored baseline, calls Nemotron via Nebius Token Factory
to explain what changed, and serves that to the dashboard.
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(title="NetPulse backend")

# Lets the dashboard (a different origin from the browser's point of
# view) actually call this API. Wide open ("*") is fine for a local
# hackathon demo — you'd lock this down to your real dashboard's
# domain before ever putting this on the public internet.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TOKEN_FACTORY_API_KEY = os.getenv("TOKEN_FACTORY_API_KEY")

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=TOKEN_FACTORY_API_KEY,
)

NEMOTRON_MODEL = "nvidia/nemotron-3-super-120b-a12b"

# Scan history lives on disk now instead of memory, so it survives a
# server restart. This is deliberately simple (one JSON file) rather
# than a database — fine for a hackathon, and easy to actually read
# yourself if you want to see what's stored.
DATA_FILE = Path(__file__).parent / "data" / "history.json"


def load_history() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {}


def save_history(history: dict) -> None:
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(history, indent=2))


class ScanPayload(BaseModel):
    subnet: str
    devices: list[dict]


def index_by_mac_or_ip(devices: list[dict]) -> dict:
    """
    Key devices by MAC address when we have one, falling back to IP.
    MAC matters here because a router's DHCP can hand a device a
    different IP address over time — the MAC is what actually stays
    constant, so it's the more reliable way to say "this is the same
    device as last time."
    """
    idx = {}
    for d in devices:
        key = d.get("mac") or d["host"]
        idx[key] = d
    return idx


def diff_scans(current: dict, previous: dict | None) -> dict | None:
    """Compute exactly what changed between two scans, in code — not left for the AI to spot."""
    if not previous:
        return None

    cur_idx = index_by_mac_or_ip(current["devices"])
    prev_idx = index_by_mac_or_ip(previous["devices"])

    new_devices = [d for k, d in cur_idx.items() if k not in prev_idx]
    missing_devices = [d for k, d in prev_idx.items() if k not in cur_idx]

    changed_ports = []
    for k in cur_idx:
        if k in prev_idx:
            cur_ports = {p["port"] for p in cur_idx[k]["open_ports"]}
            prev_ports = {p["port"] for p in prev_idx[k]["open_ports"]}
            added = cur_ports - prev_ports
            removed = prev_ports - cur_ports
            if added or removed:
                changed_ports.append({
                    "host": cur_idx[k]["host"],
                    "added_ports": sorted(added),
                    "removed_ports": sorted(removed),
                })

    return {
        "new_devices": new_devices,
        "missing_devices": missing_devices,
        "changed_ports": changed_ports,
    }


def build_prompt(current: dict, diff: dict | None) -> str:
    base = (
        "You are explaining a home network scan to a non-technical "
        "homeowner. Be specific and plain-English, not alarmist. "
        "For each notable finding, briefly say: what it is, why it "
        "might matter, and one concrete next step. Only describe "
        "devices, ports, and services that literally appear in the "
        "data below — never invent or assume findings that aren't "
        "explicitly present (no guessing about passwords, protocols, "
        "or software versions the scan didn't check).\n\n"
    )

    if diff is None:
        return (
            base
            + f"Current scan:\n{json.dumps(current, indent=2)}\n\n"
            + "This is the first scan — no history to compare against "
              "yet. Give a short overview of the whole network."
        )

    return (
        base
        + f"What changed since the last scan:\n{json.dumps(diff, indent=2)}\n\n"
        + f"Full current scan, for context:\n{json.dumps(current, indent=2)}\n\n"
        + "Focus your explanation ONLY on what changed — new devices, "
          "devices that disappeared, or newly opened/closed ports. "
          "Don't re-explain things that are unchanged from last time."
    )


def explain_with_nemotron(current: dict, diff: dict | None) -> str:
    # If we already know deterministically that nothing changed, don't
    # even ask the AI — there's nothing for it to add, and asking it
    # to "confirm" a fact it wasn't given any freedom to check is how
    # you get a hallucinated report instead of a plain true statement.
    if diff is not None:
        has_changes = diff["new_devices"] or diff["missing_devices"] or diff["changed_ports"]
        if not has_changes:
            return "No changes detected since your last scan — same devices, same open ports."

    response = client.chat.completions.create(
        model=NEMOTRON_MODEL,
        messages=[{"role": "user", "content": build_prompt(current, diff)}],
    )
    return response.choices[0].message.content



@app.post("/scan")
def receive_scan(payload: ScanPayload, x_user_token: str = Header(...)):
    """
    The agent pushes results here. x_user_token authenticates which
    user/agent this is — never trust an unauthenticated payload.
    """
    # TODO (week 6): validate x_user_token against real user records
    if not x_user_token:
        raise HTTPException(status_code=401, detail="missing auth token")

    history = load_history()
    previous = history.get(x_user_token)
    current = payload.model_dump()

    diff = diff_scans(current, previous)
    explanation = explain_with_nemotron(current, diff)

    current["explanation"] = explanation
    current["diff"] = diff

    history[x_user_token] = current
    save_history(history)

    return {
        "status": "received",
        "device_count": len(current["devices"]),
        "diff": diff,
        "explanation": explanation,
    }


@app.get("/latest")
def latest_scan(x_user_token: str = Header(...)):
    """The dashboard calls this to display current status."""
    history = load_history()
    result = history.get(x_user_token)
    if not result:
        raise HTTPException(status_code=404, detail="no scans yet")
    return result