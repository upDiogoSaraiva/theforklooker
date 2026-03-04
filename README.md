# TheFork Looker

Monitor restaurant availability on [TheFork](https://www.thefork.com) and get instant Telegram notifications when a table opens up.

Deploy a monitoring bot to a free Oracle Cloud VM with one click — no coding required.

## How It Works

1. **Download** the Windows app (`TheForkLooker.exe`)
2. **Paste** the TheFork restaurant URL
3. **Configure** which dates, party size, and meal you want
4. **Point** to your Oracle Cloud VM + SSH key
5. **Deploy** — the app installs everything and starts monitoring

The monitor checks every ~10 minutes using a real browser (Playwright + Chromium) to bypass TheFork's bot protection, and sends you a Telegram message the moment a table becomes available.

## Quick Start

### 1. Get a Free Oracle Cloud VM

1. Create an account at [cloud.oracle.com](https://cloud.oracle.com) (Always Free tier)
2. Go to **Compute > Instances > Create Instance**
3. Choose **Ubuntu 22.04** (or newer)
4. Shape: **VM.Standard.E2.1.Micro** (AMD, 1 OCPU, 1GB RAM) — Always Free
5. Under **Add SSH keys**, select **Generate a key pair** and download the private key (`.key` file)
6. Click **Create** and wait for the instance to be running
7. Copy the **Public IP** from the instance details

#### Open SSH Port (if needed)

1. Go to your instance > **Subnet** > **Security Lists**
2. Add an **Ingress Rule**: Source `0.0.0.0/0`, Protocol TCP, Port `22`

### 2. Set Up Telegram Notifications (Optional)

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`, follow the prompts, copy the **bot token**
3. Message your new bot (send any message)
4. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
5. Find `"chat":{"id":123456789}` — that's your **chat ID**

### 3. Find the Restaurant

Go to [TheFork](https://www.thefork.com), find the restaurant, and copy the URL. Example:

```
https://www.thefork.com/restaurant/o-velho-eurico-r770451
```

**If UUID auto-detection fails**, click "Reserve a table" on the restaurant page and copy the widget URL:

```
https://widget.thefork.com/en/999d3391-000e-42f1-b7bf-ce987f2f4090?step=date
```

### 4. Run the App

1. Download `TheForkLooker.exe` from [Releases](../../releases)
2. Fill in the **Setup** tab: restaurant URL, party size, dates, meal type, Telegram details
3. Fill in the **Server** tab: VM IP, SSH key file
4. Click **Test Connection** to verify
5. Go to **Deploy** tab and click **Deploy to VM**
6. Watch the progress — all 7 steps should show `[OK]`
7. Use the **Status** tab to check logs, restart, or stop

## Running from Source

```bash
git clone https://github.com/YOUR_USER/theforklooker.git
cd theforklooker

pip install paramiko

python -m app.main
```

## Building the .exe

```bash
pip install paramiko pyinstaller

build\build.bat
```

Output: `dist/TheForkLooker.exe`

## Project Structure

```
theforklooker/
├── app/
│   ├── main.py              # Entry point
│   ├── app.py               # Main controller + sidebar nav
│   ├── gui/
│   │   ├── styles.py        # Colors, fonts
│   │   ├── setup_frame.py   # Restaurant + watch config
│   │   ├── server_frame.py  # Oracle VM settings
│   │   ├── deploy_frame.py  # One-click deployment
│   │   └── status_frame.py  # View logs, restart/stop
│   ├── core/
│   │   ├── url_parser.py    # TheFork URL -> UUID
│   │   ├── config_builder.py
│   │   ├── ssh_deployer.py  # Paramiko SSH deployment
│   │   └── settings.py      # Persist form state
│   └── assets/
│       └── thefork_monitor.py  # Monitor script (deployed to VM)
├── build/
│   ├── build.bat
│   └── thefork_looker.spec
└── monitor/
    └── thefork_monitor.py      # Dev reference copy
```

## How the Monitor Works

The monitor script runs on the Oracle VM and:

1. Opens TheFork's booking widget in a headless Chromium browser
2. Injects stealth scripts to bypass DataDome bot detection
3. Calls TheFork's GraphQL API from the browser context
4. Checks if any watched dates have availability
5. Sends Telegram alerts for new openings
6. Tracks alerted dates to avoid duplicate notifications
7. Uses clock-aligned scheduling (e.g., checks at :01, :11, :21, :31, :41, :51)

## License

MIT
