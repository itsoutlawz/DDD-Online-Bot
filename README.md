# DamaDam Online Bot

![DamaDam Logo](https://via.placeholder.com/150x50?text=DamaDam) <!-- You can replace this with an actual logo if available -->

## Overview

**DamaDam Online Bot** is a lightweight, single-file Python scraper designed to fetch the latest posts from currently online users on the DamaDam platform. It automatically writes the scraped data to a Google Sheet named **ProfilesOnline**, keeping your data organized and up-to-date. This bot is perfect for monitoring user activity in real-time without manual intervention.

- **Version**: v3.2.1
- **Author**: itsoutlawz
- **Purpose**: Scrape and track online user profiles and posts from DamaDam efficiently.

Whether you're running it locally for testing or automating it via GitHub Actions for scheduled updates, this bot handles duplicates, tracks user history, and respects API limits to ensure smooth operation.

## Features

- **Real-Time Scraping**: Captures the latest posts from online users on DamaDam.
- **Google Sheets Integration**: Inserts new/updated data at the top (Row 2) for easy viewing.
- **Duplicate Detection**: Checks by nickname (Column B) and highlights changes with annotations.
- **Adaptive Delays**: Built-in throttling to avoid hitting Google API quotas.
- **User Tracking**: Maintains a **NickList** worksheet with stats like times seen, first seen, and last seen timestamps.
- **Multi-Account Support**: Optional second set of DamaDam credentials for enhanced scraping.
- **Automated Workflows**: Seamless integration with GitHub Actions for scheduled or manual runs.

## Requirements

This project uses Python 3.x and a few key libraries. No complex setup needed!

### Dependencies
Install via `requirements.txt`:
- `requests` (for HTTP requests)
- `google-api-python-client` (for Sheets API)
- `google-auth` and `google-auth-oauthlib` (for authentication)
- Other utilities like `beautifulsoup4` for parsing (if used in scraping)

## Installation

1. **Clone the Repository**:
   ```
   git clone https://github.com/itsoutlawz/DDD-Online-Bot.git
   cd DDD-Online-Bot
   ```

2. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Set Up Google Sheets**:
   - Create a Google Sheet and note its URL (e.g., `https://docs.google.com/spreadsheets/d/<SHEET_ID>`).
   - Set up a Service Account in Google Cloud Console:
     - Enable Google Sheets API.
     - Download the JSON credentials file.
   - Share the sheet with the service account email (found in the JSON).

4. **Configure Secrets** (for GitHub Actions or local env):
   See the [Secrets Setup](#secrets-setup) section below.

## Usage

### Local Run
Simply execute the main script:
```
python Scraper.py
```

- The bot will log in to DamaDam using your credentials.
- Scrape online users and posts.
- Update the **ProfilesOnline** sheet with new data.
- Maintain the **NickList** for tracking.

### GitHub Actions
- The repo includes a workflow for automated runs (manual dispatch or cron-scheduled).
- It dynamically creates `google_credentials.json` from secrets and sets environment variables.
- Trigger via GitHub UI: Go to **Actions** > Select workflow > **Run workflow**.

#### Example Output in Sheets
- **ProfilesOnline Sheet**: Columns like Timestamp, Nickname, Post Content, etc. New rows pushed to the top.
- **NickList Sheet**: Tracks each unique nick with counters and timestamps.

## Secrets Setup

For security, store sensitive info as GitHub Secrets (or environment variables for local runs):

| Secret Name              | Description                          | Example Value |
|--------------------------|--------------------------------------|---------------|
| `DAMADAM_USERNAME`      | Primary DamaDam login username      | your_username |
| `DAMADAM_PASSWORD`      | Primary DamaDam login password      | your_password |
| `DAMADAM_USERNAME_2`    | Optional second username            | alt_username  |
| `DAMADAM_PASSWORD_2`    | Optional second password            | alt_password  |
| `GOOGLE_SHEET_URL`      | Full URL to your Google Sheet       | https://docs.google.com/spreadsheets/d/1ABC... |
| `GOOGLE_CREDENTIALS_JSON` | JSON string from Service Account   | {"type": "service_account", ...} |

**Local Tip**: Export these as env vars, e.g., `export DAMADAM_USERNAME=your_username`.

## Project Structure

```
DDD-Online-Bot/
├── Scraper.py              # Main scraping and Sheets logic
├── requirements.txt        # Python dependencies
├── google_credentials.json # Auto-generated from secrets (gitignore'd)
└── .github/workflows/      # CI/CD workflows (if present)
    └── scraper.yml
```

## Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repo and create a feature branch (`git checkout -b feature/amazing-feature`).
2. Commit your changes (`git commit -m 'Add amazing feature'`).
3. Push to the branch (`git push origin feature/amazing-feature`).
4. Open a Pull Request.

Please ensure code follows PEP 8 style and includes tests if applicable.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. (Add one if not present!)

## Support & Issues

- Found a bug? Open an [issue](https://github.com/itsoutlawz/DDD-Online-Bot/issues).
- Questions? Feel free to reach out via GitHub Discussions.

**Happy Scraping!** 🚀
