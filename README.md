# livewire-pairing

Pairs a device with your LiveWire motorcycle so that [evcc](https://evcc.io) can read its charging state.

evcc talks to the same cloud API as the LiveWire app. That API only answers devices that have been paired with the motorcycle once. Pairing requires a code shown on the bike's display, so it cannot happen inside evcc. This script does it for you and prints the device UUID that goes into the evcc configuration.

## Requirements

- Python 3.8 or newer, no additional packages
- Your LiveWire account credentials
- Being at the motorcycle once, ignition on

## Usage

```
python livewire-pair.py
```

The script asks for your account email and password, lists your motorcycles, sends the pairing request and asks for the code that appears on the display. When the pairing is confirmed it prints the UUID:

```
    deviceUUID: 6ba7b810-9dad-11d1-80b4-00c04fd430c8
```

Enter this value in evcc, either in the UI (vehicle type LiveWire, field "Device UUID") or in `evcc.yaml`:

```yaml
vehicles:
  - name: livewire
    type: livewire
    user: <your LiveWire account email>
    password: <your password>
    deviceUUID: 6ba7b810-9dad-11d1-80b4-00c04fd430c8
```

Keep the UUID. It identifies this pairing; running the script again generates a new one and needs another trip to the motorcycle.

To check whether an existing UUID is still paired, or to pair it again:

```
python livewire-pair.py --device-uuid <uuid>
```

Credentials can also be passed through the environment variables `LW_USER` and `LW_PASS`.

## What it does

1. Logs in to the LiveWire account (Gigya) and opens an API session for the generated device UUID
2. Lists the motorcycles on the account together with their pairing status
3. `POST /bikes/{id}/pair` makes the motorcycle display a code
4. `POST /bikes/{id}/verify/code` sends that code back
5. Polls `pairing/status` until the backend confirms

Nothing is stored on disk. The credentials are only used for the login and never leave your machine except towards the LiveWire servers.

This is not affiliated with LiveWire or Harley-Davidson. The API is undocumented and may change.
