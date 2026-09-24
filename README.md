# livewire-pairing

> **Disclaimer:** This project is not affiliated with, endorsed by or supported by LiveWire or Harley-Davidson. It uses the undocumented API of the LiveWire app, which may change or stop working at any time. Use at your own risk.

Pairs a device with your LiveWire motorcycle so that [evcc](https://evcc.io) can read its charging state.

evcc talks to the same cloud API as the LiveWire app. That API only answers devices that have been paired with the motorcycle once. Pairing requires a code shown on the bike's display, so it cannot happen inside evcc. This script does it for you and prints the device UUID that goes into the evcc configuration.

Tested only with a LiveWire S2 (2025 Mulholland). Other models such as the LiveWire One or the S4 may use a different pairing flow and are not guaranteed to work. If you try one, please open an issue with the result.

## Requirements

- Your LiveWire account credentials
- Being at the motorcycle once, ignition on

## Usage

Pick whichever of these is easiest for you. They all run the same script.

### Option 1: Download the program (no Python needed)

Download the file for your system from the [latest release](https://github.com/j4velin/livewire-pairing/releases/latest) and start it:

- **Windows:** `livewire-pair-windows.exe`, double-click it. SmartScreen may warn about an unknown publisher; choose "More info" → "Run anyway".
- **macOS:** `livewire-pair-macos` (Apple Silicon). In Terminal: `chmod +x livewire-pair-macos && xattr -d com.apple.quarantine livewire-pair-macos && ./livewire-pair-macos`
- **Linux:** `livewire-pair-linux`, then `chmod +x livewire-pair-linux && ./livewire-pair-linux`

The files are built from this repository by [GitHub Actions](.github/workflows/release.yml).

### Option 2: Run it in the browser (nothing to download)

Needs a free GitHub account. This works from a phone too, which is handy when standing next to the motorcycle.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/j4velin/livewire-pairing?quickstart=1)

Once the codespace has loaded, type into the terminal at the bottom:

```
python livewire-pair.py
```

The script then runs on a virtual machine of GitHub in your account. Delete the codespace afterwards under [github.com/codespaces](https://github.com/codespaces).

### Option 3: Run it with Python

Requires Python 3.8 or newer, no additional packages.

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

Nothing is stored on disk. The credentials are only used for the login and are only sent to the LiveWire servers (in a codespace, they pass through the virtual machine GitHub runs for you).

## License

MIT, see [LICENSE](LICENSE).
