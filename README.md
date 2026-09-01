# NetPulse

Plain-English home network security monitoring, powered by NVIDIA Nemotron on Nebius Token Factory.

> Built for the Nebius x NVIDIA Global AI Hackathon.

## The problem

Most people have no idea what's actually connected to their home WiFi, or whether any of it is a security risk. The tools that could tell them (nmap, network scanners) are built for IT professionals, not regular people.

## What it does

NetPulse runs a lightweight scanner inside your home network, learns what "normal" looks like (your devices, their usual ports), and flags what changes — a new device joining, a newly exposed port, an outdated smart-home gadget with a known weak spot. Nemotron turns the raw technical findings into plain-English explanations and next steps.

## Architecture

Two halves, split by a hard boundary: a website alone can't reach into your home network (private IP addressing), so scanning has to happen locally.

- **`agent/`** — runs *inside* the home network. Discovers devices (ARP), scans ports (nmap), packages results as JSON, and pushes them out. It never accepts inbound commands — outbound-only by design, so it can't become a remote-control backdoor into someone's home network.
- **`backend/`** — cloud API. Receives scan results, compares against the stored baseline to detect what changed, calls Nemotron via Nebius Token Factory to generate plain-English explanations, and serves the dashboard.
- **`dashboard/`** — the public web page showing current devices, flagged issues, and a timeline of changes.

## Security principles

- Agent → backend is one-way (push only). The agent never listens for or accepts commands.
- Agent opens no inbound ports of its own.
- TLS + per-user auth token between agent and backend.
- Detection only — no exploitation attempts, no credential testing against discovered devices.
- Scans only the local subnet the agent is installed on, only with explicit user action.
- Minimal data retention — no permanent detailed network maps.

## Setup

### Agent (run on a device inside your home network)
```bash
cd agent
pip install -r requirements.txt
python scanner.py
```

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # add your Token Factory API key
uvicorn main:app --reload
```

### Dashboard
See `dashboard/README.md` (coming in later build phase).

## Built with

- [NVIDIA Nemotron](https://developer.nvidia.com/nemotron) via [Nebius Token Factory](https://tokenfactory.nebius.com)

## Team

- Faris — [add role/partner name here]

## License

MIT — see [LICENSE](./LICENSE)
