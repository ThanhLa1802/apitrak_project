"""
simulate_devices.py — Real-time device movement simulator for ApiTrak.

Sends telemetry pings to the FastAPI ingestion service every PING_INTERVAL
seconds, making each device "drive" along a random walk around Ha Noi.

Usage:  python simulate_devices.py
"""

import math
import os
import random
import time
from datetime import datetime, timezone

import requests

# ── SETTINGS — edit these ─────────────────────────────────────────────────────

INGEST_URL: str = os.getenv("INGEST_URL", "http://localhost:8001")
PING_INTERVAL: float = float(os.getenv("PING_INTERVAL", "3"))

# Add one entry per device. api_key = raw key you typed when creating the device.
DEVICES: list[dict] = [
    {"api_key": "test-key2", "label": "Device 1"},
    # {"api_key": "REPLACE_WITH_YOUR_API_KEY_2", "label": "Device 2"},
]

BASE_LAT: float = 21.0285   # Ha Noi
BASE_LNG: float = 105.8542
STEP_SIZE: float = 0.0005   # ~55 m per step

# ── Simulator ─────────────────────────────────────────────────────────────────

_session = requests.Session()


def _heading(dlat: float, dlng: float) -> float:
    return math.degrees(math.atan2(dlng, dlat)) % 360


class DeviceSimulator:
    def __init__(self, api_key: str, label: str) -> None:
        self.api_key = api_key
        self.label = label
        self.lat = BASE_LAT + random.uniform(-0.005, 0.005)
        self.lng = BASE_LNG + random.uniform(-0.005, 0.005)
        self.speed = random.uniform(20, 60)
        self.battery = 100

    def step(self) -> dict:
        dlat = random.uniform(-STEP_SIZE, STEP_SIZE)
        dlng = random.uniform(-STEP_SIZE, STEP_SIZE)
        self.lat += dlat
        self.lng += dlng
        self.speed = max(5.0, min(120.0, self.speed + random.uniform(-5, 5)))
        self.battery = max(1, self.battery - random.randint(0, 1))
        return {
            "lat": round(self.lat, 6),
            "lng": round(self.lng, 6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "speed": round(self.speed, 1),
            "heading": round(_heading(dlat, dlng), 1),
            "accuracy": round(random.uniform(3.0, 15.0), 1),
            "battery": self.battery,
        }

    def send(self) -> None:
        payload = self.step()
        try:
            resp = _session.post(
                f"{INGEST_URL}/ingest",
                json=payload,
                headers={"X-API-Key": self.api_key},
                timeout=5,
            )
            ok = "OK" if resp.status_code == 202 else f"FAIL {resp.status_code} {resp.text[:80]}"
            print(
                f"  [{self.label}] lat={payload['lat']} lng={payload['lng']} "
                f"speed={payload['speed']} hdg={payload['heading']} "
                f"bat={payload['battery']}%  -> {ok}"
            )
        except requests.RequestException as exc:
            print(f"  [{self.label}] ERROR: {exc}")


def main() -> None:
    unconfigured = [d for d in DEVICES if d["api_key"].startswith("REPLACE_")]
    if unconfigured:
        print("ERROR: Replace placeholder api_key values with real device keys.")
        print("  Go to Devices page -> create a device -> copy the API key you typed.")
        return

    sims = [DeviceSimulator(d["api_key"], d["label"]) for d in DEVICES]
    print(f"Simulating {len(sims)} device(s) -> {INGEST_URL}/ingest")
    print(f"Ping every {PING_INTERVAL}s | Ctrl+C to stop\n")

    ping = 0
    while True:
        ping += 1
        print(f"-- Ping #{ping} " + "-" * 40)
        for s in sims:
            s.send()
        time.sleep(PING_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
