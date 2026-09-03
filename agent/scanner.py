"""
NetPulse local scanner agent.

Runs INSIDE the home network (not in the cloud) because private IPs
like 192.168.x.x are only reachable from devices on the same network.

Two-stage scan:
  1. Host discovery — find what's alive on the subnet (ARP-based).
  2. Port scan — for each live host, check common ports to see what
     services are running and potentially exposed.

This agent is outbound-only by design: it never opens a listening
port and never accepts commands from the backend. It only ever
pushes scan results out. See README.md "Security principles".
"""

import json
import nmap
import requests

SUBNET = "192.168.68.0/24"

COMMON_PORTS = "21,22,23,80,443,445,3389,8080"


def discover_hosts(scanner: nmap.PortScanner, subnet: str) -> list[str]:
    """Stage 1: find live hosts on the subnet using a ping/ARP scan (-sn)."""
    scanner.scan(hosts=subnet, arguments="-sn")
    return scanner.all_hosts()


def scan_ports(scanner: nmap.PortScanner, host: str, ports: str) -> dict:
    """Stage 2: check which of the given ports are open on this host."""
    scanner.scan(hosts=host, ports=ports, arguments="-T4")
    if host not in scanner.all_hosts():
        return {}

    open_ports = []
    tcp_results = scanner[host].get("tcp", {})
    for port, info in tcp_results.items():
        if info.get("state") == "open":
            open_ports.append({
                "port": port,
                "service": info.get("name", "unknown"),
            })
    return {
        "host": host,
        "mac": scanner[host]["addresses"].get("mac"),
        "open_ports": open_ports,
    }


def run_scan() -> dict:
    scanner = nmap.PortScanner()
    print(f"Discovering devices on {SUBNET} ...")
    hosts = discover_hosts(scanner, SUBNET)
    print(f"Found {len(hosts)} device(s). Checking ports...")

    results = []
    for host in hosts:
        result = scan_ports(scanner, host, COMMON_PORTS)
        if result:
            results.append(result)

    return {"subnet": SUBNET, "devices": results}


BACKEND_URL = "http://127.0.0.1:8000/scan"
USER_TOKEN = "test123"


def send_to_backend(scan_results: dict) -> dict:
    response = requests.post(
        BACKEND_URL,
        json=scan_results,
        headers={"x-user-token": USER_TOKEN},
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    scan_results = run_scan()
    print(json.dumps(scan_results, indent=2))

    print("\nSending to backend...")
    result = send_to_backend(scan_results)
    print("\n--- Nemotron's explanation ---\n")
    print(result["explanation"])