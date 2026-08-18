# PCPolish

**Fast, ad-free Windows system optimizer.**

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078d4?logo=windows)
![License](https://img.shields.io/badge/license-Commercial-blue)

> One app to clean junk, fix the registry, manage startup, analyze disk space, and boost PC performance — no subscriptions, no ads, no tracking.

**[Get PCPolish — £19.99 lifetime](https://pcpolish.com)**

---

## Features

| Tool | What it does |
|---|---|
| **PC Health Check** | Scores your system across 10 metrics (disk, RAM, CPU, junk, registry, updates…) |
| **Custom Cleaner** | Removes temp files, Windows cache, log files, installer leftovers |
| **Registry Cleaner** | Scans 8 categories — invalid paths, orphaned keys, broken COM refs — and fixes safely |
| **Browser Cleaner** | Clears Chrome/Edge cache, cookies, history |
| **Startup Manager** | View and disable programs that slow boot time |
| **Disk Analyzer** | Visual breakdown of what's eating storage |
| **Duplicate Finder** | Find and remove identical files |
| **Secure Wiper** | Multi-pass file erasure beyond recovery |
| **Uninstaller** | Remove software cleanly |
| **Software Updater** | Detect outdated software |
| **Performance Optimizer** | Tune Windows settings for speed |
| **Cookie Manager** | Granular browser cookie control |
| **Scheduler** | Automate cleaning on a schedule |

## Licensing

PCPolish is commercial software.

- **7-day free trial** — full features, no card required
- **£19.99 one-time** — lifetime licence, all future updates included
- Activate on up to **3 devices** per licence
- No subscription, no ads, no telemetry

## Quick Start

1. Download the latest release
2. Extract anywhere
3. Run `run.exe`

No Python required. No installation. Works on Windows 10 & 11.

## Run from Source

```bash
pip install -r requirements.txt
python main.py
```

## Build

```bash
pip install pyinstaller
pyinstaller PCPolish.spec --clean --noconfirm
```

Output: `dist/PCPolish/run.exe`

## License

Copyright © 2026. All rights reserved.

This software is commercial and proprietary. Source is published for
transparency — you can read and audit exactly what runs on your machine.
It is not licensed for redistribution or commercial reuse.
