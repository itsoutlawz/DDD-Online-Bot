
# DamaDam Online Bot (Single-File) — v3.2.1
[![DDD Online Bot](https://github.com/itsoutlawz/DDD-Online-Bot/actions/workflows/online-bot.yml/badge.svg?branch=main)](https://github.com/itsoutlawz/DDD-Online-Bot/actions/workflows/online-bot.yml)
- Scrapes currently online users and writes to Google Sheets (ProfilesOnline).
- New and updated rows insert at Row 2 (latest on top).
- Duplicate check by Nickname (Col B); changed cells highlighted and annotated.
- Adaptive delay to respect Google API limits.

## Secrets (GitHub Actions)

```ini
DAMADAM_USERNAME=...
DAMADAM_PASSWORD=...
DAMADAM_USERNAME_2=... (optional)
DAMADAM_PASSWORD_2=... (optional)
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/<sheet-id>
GOOGLE_CREDENTIALS_JSON={ ... service account json ... }
```

## Run locally

```bash
pip install -r requirements.txt
python Scraper.py
```

## GitHub Actions
- Manual dispatch and schedule supported.
- The workflow writes GOOGLE_CREDENTIALS_JSON to google_credentials.json and sets GOOGLE_APPLICATION_CREDENTIALS.

