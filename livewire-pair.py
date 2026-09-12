#!/usr/bin/env python3
"""Pair a device with your LiveWire motorcycle for use with evcc.

evcc reads the charging state of a LiveWire through the same cloud API as the
LiveWire app. The API only answers for devices that have been paired with the
motorcycle once, which requires a code shown on the bike's display. This script
performs that pairing and prints the device UUID to put into the evcc config.

Requirements: Python 3.8 or newer, no extra packages. You need to be at the
motorcycle with the ignition on.

Usage:
    python livewire-pair.py
    python livewire-pair.py --device-uuid <uuid>   # check or re-pair an existing uuid

Credentials can also be passed via the environment (LW_USER, LW_PASS).
"""

import argparse
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

GIGYA_URL = "https://accounts.us1.gigya.com"
GIGYA_API_KEY = "4_6aX8cf8RFVt6F3JQQZaF3A"
DATA_CENTER = "us1"
BASE_URL = "https://mobileapi.livewire.com/api"
BRAND = "LiveWire"

CLIENT_HEADERS = {
    "User-Agent": "Android",
    "Content-Type": "application/json",
    "Accept-Language": "en-US",
    "model": "Pixel 8",
    "osVersion": "34",
}


class ApiError(Exception):
    pass


def request(method, url, body=None, headers=None):
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        raise ApiError(f"cannot reach {url}: {e.reason}") from None


def parse(body):
    try:
        return json.loads(body)
    except ValueError:
        return {"raw": body.decode(errors="replace")}


def gigya_uid(user, password):
    form = urllib.parse.urlencode({
        "apiKey": GIGYA_API_KEY,
        "loginID": user,
        "password": password,
        "include": "profile,data",
        "format": "json",
    }).encode()
    status, body = request("POST", f"{GIGYA_URL}/accounts.login", form,
                           {"Content-Type": "application/x-www-form-urlencoded"})
    res = parse(body)
    if status != 200 or res.get("errorCode", 0) != 0:
        raise ApiError(f"login failed: {res.get('errorMessage', body)} (code {res.get('errorCode')})")
    return res["UID"]


def session(uid, device_uuid):
    status, body = request("POST", f"{BASE_URL}/session",
                           {"UID": uid, "deviceUUID": device_uuid, "dataCenter": DATA_CENTER},
                           CLIENT_HEADERS)
    res = parse(body)
    if status != 200 or not res.get("jwt"):
        raise ApiError(f"session failed (HTTP {status}): {res}")
    return res["jwt"]


class Api:
    def __init__(self, jwt, device_uuid):
        self.headers = dict(CLIENT_HEADERS, Authorization=f"Bearer {jwt}")
        self.device_uuid = device_uuid

    def call(self, method, path, body=None):
        sep = "&" if "?" in path else "?"
        url = f"{BASE_URL}{path}{sep}brand={BRAND}&deviceUUID={self.device_uuid}"
        status, raw = request(method, url, body, self.headers)
        res = parse(raw)
        if status >= 400:
            raise ApiError(f"{method} {path} failed (HTTP {status}): {res}")
        if isinstance(res, dict) and "error" in res:
            err = res["error"]
            raise ApiError(f"{method} {path} failed: {err.get('description')} (code {err.get('code')})")
        return res

    def bikes(self):
        return self.call("GET", "/getAllbikes/pairingStatus").get("bikes", [])

    def pair(self, bike_id):
        return self.call("POST", f"/bikes/{bike_id}/pair", {})

    def verify(self, bike_id, code):
        return self.call("POST", f"/bikes/{bike_id}/verify/code", {"code": code})

    def paired(self, bike_id):
        return bool(self.call("GET", f"/bikes/pairing/status/{bike_id}").get("pairingStatus"))


def choose_bike(bikes):
    if not bikes:
        sys.exit("No motorcycles found on this account.")
    if len(bikes) == 1:
        return bikes[0]

    print("\nMotorcycles on this account:")
    for i, b in enumerate(bikes, 1):
        state = "paired" if b.get("pairingStatus") else "not paired"
        print(f"  {i}. {b.get('year', '')} {b.get('model', '')} \"{b.get('name', '')}\"  VIN {b.get('vin')}  ({state})")
    while True:
        choice = input(f"Which one? [1-{len(bikes)}] ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(bikes):
            return bikes[int(choice) - 1]


def print_result(device_uuid, bike):
    print("\n" + "=" * 64)
    print("Pairing complete. Put this into your evcc configuration:")
    print()
    print(f"    deviceUUID: {device_uuid}")
    print()
    print("Keep the value. It identifies this pairing; a different UUID needs")
    print("pairing again at the motorcycle.")
    print("=" * 64)
    print("\nExample evcc.yaml:\n")
    print("vehicles:")
    print("  - name: livewire")
    print("    type: livewire")
    print("    user: <your LiveWire account email>")
    print("    password: <your password>")
    print(f"    deviceUUID: {device_uuid}")
    if bike.get("vin"):
        print(f"    vin: {bike['vin']}   # optional with a single motorcycle")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--device-uuid", help="reuse an existing device uuid instead of generating one")
    args = ap.parse_args()

    device_uuid = args.device_uuid or str(uuid.uuid4())
    try:
        uuid.UUID(device_uuid)
    except ValueError:
        sys.exit(f"not a valid uuid: {device_uuid}")

    user = os.environ.get("LW_USER") or input("LiveWire account email: ").strip()
    password = os.environ.get("LW_PASS") or getpass.getpass("Password: ")

    print("\nLogging in...")
    jwt = session(gigya_uid(user, password), device_uuid)
    api = Api(jwt, device_uuid)

    bike = choose_bike(api.bikes())
    bike_id = str(bike["id"])
    print(f"\nMotorcycle: {bike.get('year', '')} {bike.get('model', '')} \"{bike.get('name', '')}\" (VIN {bike.get('vin')})")

    if bike.get("pairingStatus"):
        print(f"Device {device_uuid} is already paired with this motorcycle.")
        print_result(device_uuid, bike)
        return

    print("\nGo to the motorcycle, switch the ignition on and wake the display.")
    input("Press Enter to send the pairing request... ")

    api.pair(bike_id)
    print("\nThe motorcycle should now show a pairing code.")
    code = input("Enter the code shown on the display: ").strip()
    if not code:
        sys.exit("No code entered.")

    api.verify(bike_id, code)

    for _ in range(12):
        if api.paired(bike_id):
            print_result(device_uuid, bike)
            return
        time.sleep(5)

    sys.exit("The motorcycle did not confirm the pairing. Check the code and run the script again.")


if __name__ == "__main__":
    try:
        main()
    except ApiError as e:
        sys.exit(f"\nError: {e}")
    except KeyboardInterrupt:
        sys.exit("\nAborted.")
