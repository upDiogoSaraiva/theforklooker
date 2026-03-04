# TheFork Looker

Monitor restaurant availability on [TheFork](https://www.thefork.com) and get Telegram notifications when a table opens up.

Deploys a monitoring bot to a free Oracle Cloud VM with one click. No coding required.

## How It Works

1. Download the Windows app (`TheForkLooker.exe`)
2. Paste the TheFork restaurant URL
3. Configure which dates, party size, and meal you want
4. Point to your Oracle Cloud VM and SSH key
5. Hit Deploy

The monitor checks every ~10 minutes using a real browser (Playwright + Chromium) to bypass TheFork's bot protection, and sends a Telegram message the moment a table becomes available.

## Quick Start

### 1. Get a Free Oracle Cloud VM

Create an account at [cloud.oracle.com](https://cloud.oracle.com) (Always Free tier), then go to Compute > Instances > Create Instance.

Pick **Ubuntu 22.04** (or newer), shape **VM.Standard.E2.1.Micro** (AMD, 1 OCPU, 1GB RAM, Always Free eligible). Under "Add SSH keys", generate a key pair and download the private key (`.key` file). Create the instance and copy the **Public IP** from the details page.

**Open SSH port (if needed):** Go to your instance > Subnet > Security Lists. Add an Ingress Rule with source `0.0.0.0/0`, protocol TCP, port `22`.

### 2. Set Up Telegram Notifications (Optional)

Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, follow the prompts, and copy the **bot token**. Then message your new bot (send anything), and visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` to find your **chat ID** (`"chat":{"id":123456789}`).

### 3. Find the Restaurant

Go to [TheFork](https://www.thefork.com), find the restaurant, and copy the URL:

```
https://www.thefork.com/restaurant/o-velho-eurico-r770451
```

If UUID auto-detection fails, click "Reserve a table" on the restaurant page and copy the widget URL instead:

```
https://widget.thefork.com/en/999d3391-000e-42f1-b7bf-ce987f2f4090?step=date
```

### 4. Run the App

Download `TheForkLooker.exe` from [Releases](../../releases). Fill in the Setup tab (restaurant URL, party size, dates, meal type, Telegram details), then the Server tab (VM IP, SSH key file). Test the connection, go to Deploy, and hit Deploy to VM. All 7 steps should show `[OK]`. Use the Status tab to check logs, restart, or stop.

## Running from Source

```bash
git clone https://github.com/upDiogoSaraiva/theforklooker.git
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
│   ├── main.py                  Entry point
│   ├── app.py                   Main controller + sidebar nav
│   ├── gui/
│   │   ├── styles.py            Colors, fonts
│   │   ├── setup_frame.py       Restaurant + watch config
│   │   ├── server_frame.py      Oracle VM settings
│   │   ├── deploy_frame.py      One-click deployment
│   │   └── status_frame.py      View logs, restart/stop
│   ├── core/
│   │   ├── url_parser.py        TheFork URL -> UUID
│   │   ├── config_builder.py
│   │   ├── ssh_deployer.py      Paramiko SSH deployment
│   │   └── settings.py          Persist form state
│   └── assets/
│       └── thefork_monitor.py   Monitor script (deployed to VM)
├── build/
│   ├── build.bat
│   └── thefork_looker.spec
└── monitor/
    └── thefork_monitor.py       Dev reference copy
```

## How the Monitor Works

The monitor script runs on the Oracle VM. It opens TheFork's booking widget in a headless Chromium browser, injects stealth scripts to bypass DataDome bot detection, and calls TheFork's GraphQL API from the browser context. It checks if any watched dates have availability, sends Telegram alerts for new openings, and tracks alerted dates to avoid duplicates. Scheduling is clock-aligned (e.g. checks fire at :01, :11, :21, :31, :41, :51).

## License

MIT
