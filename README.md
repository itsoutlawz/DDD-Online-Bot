# 🌐 DamaDam Online Bot — v3.2.1

> **Smart Scheduling Edition** — Scrapes all online users without timeout interruptions!

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Smart Scheduling** | Processes complete profile list; waits if < 15min, runs immediately if > 15min |
| 🔐 **Smart Login** | Tries cookies first → Account 1 → Account 2 with detailed logging |
| 📊 **Google Sheets Integration** | Auto-writes to ProfilesOnline sheet with latest profiles at top |
| 🔍 **Duplicate Detection** | Checks by Nickname (Column B); updates existing profiles |
| 🎨 **Professional Formatting** | Courier New font, bold headers, alternating row colors, frozen headers |
| 📈 **Adaptive Delays** | Respects Google Sheets API rate limits with intelligent backoff |
| 🛡️ **Quota-Aware** | Gracefully handles API quota limits without crashing |
| 👤 **Nick Tracking** | Maintains NickList worksheet with Times Seen, First Seen, Last Seen |
| 📱 **Responsive** | Handles suspended accounts, unverified users, and missing data gracefully |
| 📋 **Detailed Logging** | Color-coded output with progress bars and ETA calculations |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Chrome/Chromium browser
- Google Service Account credentials
- DamaDam.pk login credentials

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/DDD-Online-Bot.git
cd DDD-Online-Bot

# Install dependencies
pip install -r requirements.txt
```

### Local Setup

1. **Create `.env` file** (optional, for local testing):
```bash
DAMADAM_USERNAME=your_username
DAMADAM_PASSWORD=your_password
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

2. **Run locally**:
```bash
python Scraper.py
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DAMADAM_USERNAME` | ✅ | Primary account username | `user123` |
| `DAMADAM_PASSWORD` | ✅ | Primary account password | `pass123` |
| `DAMADAM_USERNAME_2` | ❌ | Secondary account (fallback) | `user456` |
| `DAMADAM_PASSWORD_2` | ❌ | Secondary account password | `pass456` |
| `GOOGLE_SHEET_URL` | ✅ | Google Sheets URL | `https://docs.google.com/spreadsheets/d/...` |
| `GOOGLE_CREDENTIALS_JSON` | ✅ | Service account JSON (raw) | `{"type":"service_account",...}` |
| `MAX_PROFILES_PER_RUN` | ❌ | Limit profiles (0 = unlimited) | `0` |
| `BATCH_SIZE` | ❌ | Profiles per batch before cooldown | `10` |
| `MIN_DELAY` | ❌ | Min delay between requests (sec) | `0.5` |
| `MAX_DELAY` | ❌ | Max delay between requests (sec) | `0.7` |
| `PAGE_LOAD_TIMEOUT` | ❌ | Page load timeout (sec) | `30` |
| `SHEET_WRITE_DELAY` | ❌ | Delay between sheet writes (sec) | `1.0` |

---

## 🔐 GitHub Actions Setup

### Step 1: Create Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Google Sheets API** and **Google Drive API**
4. Create a **Service Account**:
   - Go to **Service Accounts** → **Create Service Account**
   - Grant roles: `Editor`
   - Create a **JSON key**
5. Copy the entire JSON content

### Step 2: Create Google Sheet

1. Create a new Google Sheet
2. Share it with the service account email (found in the JSON key)
3. Copy the sheet URL

### Step 3: Add GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `DAMADAM_USERNAME` | Your DamaDam username |
| `DAMADAM_PASSWORD` | Your DamaDam password |
| `DAMADAM_USERNAME_2` | Secondary username (optional) |
| `DAMADAM_PASSWORD_2` | Secondary password (optional) |
| `GOOGLE_SHEET_URL` | Your Google Sheet URL |
| `GOOGLE_CREDENTIALS_JSON` | Entire service account JSON |

### Step 4: Workflow Configuration

The workflow runs:
- **Automatically**: Every 15 minutes (cron: `*/15 * * * *`)
- **Manually**: Via GitHub Actions dispatch

#### Adjust Schedule

Edit `.github/workflows/online-bot.yml`:

```yaml
on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes
    # - cron: '0 */6 * * *'  # Every 6 hours
    # - cron: '0 9 * * *'    # Daily at 9 AM UTC
```

---

## 📊 Data Structure

### ProfilesOnline Sheet

| Column | Type | Description |
|--------|------|-------------|
| IMAGE | Image | Profile avatar |
| NICK NAME | Text | Username |
| TAGS | Text | Custom tags (from Tags sheet) |
| LAST POST | Link | Link to latest post |
| LAST POST TIME | Date | When the post was made |
| FRIEND | Text | Friend status (Yes/No) |
| CITY | Text | User's city |
| GENDER | Emoji | 💃 Female / 🕺 Male |
| MARRIED | Emoji | 💍 Married / ❎ Single |
| AGE | Number | User's age |
| JOINED | Date | Account creation date |
| FOLLOWERS | Number | Follower count |
| STATUS | Text | Verified / Unverified / Suspended |
| POSTS | Number | Total posts |
| PROFILE LINK | Link | Direct profile URL |
| INTRO | Text | Bio/introduction |
| SOURCE | Text | Always "Online" |
| DATETIME SCRAP | DateTime | When profile was scraped |

### NickList Sheet

Tracks every unique nickname seen:

| Column | Description |
|--------|-------------|
| Nick Name | Username |
| Times Seen | How many times encountered |
| First Seen | First appearance timestamp |
| Last Seen | Most recent appearance timestamp |

### Dashboard Sheet

Run statistics and metrics:

| Column | Description |
|--------|-------------|
| Run# | Sequential run number |
| Timestamp | When the run completed |
| Profiles | Total profiles processed |
| Success | Successfully scraped |
| Failed | Failed scrapes |
| New | New profiles added |
| Updated | Existing profiles updated |
| Unchanged | Profiles with no changes |
| Trigger | Scheduled / Manual |
| Start | Run start time |
| End | Run end time |

---

## 🎯 How Smart Scheduling Works

```
┌─────────────────────────────────────────┐
│  Workflow Triggered (Every 15 min)      │
└──────────────┬──────────────────────────┘
               │
               ▼
        ┌──────────────┐
        │ Fetch Online │
        │   Profiles   │
        └──────┬───────┘
               │
               ▼
        ┌──────────────────┐
        │ Scrape & Update  │
        │  All Profiles    │
        └──────┬───────────┘
               │
               ▼
        ┌──────────────────────────┐
        │ Measure Execution Time   │
        └──────┬───────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
   < 15 min      ≥ 15 min
        │             │
        ▼             ▼
    Wait for    Start Next
   15 min mark   Run Now
        │             │
        └──────┬──────┘
               │
               ▼
        ┌──────────────┐
        │ Next Cycle   │
        └──────────────┘
```

**Benefits:**
- ✅ Always completes full profile list (no timeouts)
- ✅ No "Run Cancelled" emails
- ✅ Consistent 15-minute intervals
- ✅ Handles variable scraping times gracefully

---

## 🛠️ Troubleshooting

### ❌ "Login failed"
- Verify credentials in GitHub Secrets
- Check if account is locked or suspended
- Try secondary account (DAMADAM_USERNAME_2)

### ❌ "Google auth failed"
- Ensure service account has Editor role
- Verify sheet is shared with service account email
- Check JSON credentials are valid

### ❌ "Browser setup failed"
- Chrome/Chromium must be installed
- GitHub Actions uses `browser-actions/setup-chrome@v1`

### ⚠️ "Rate limit hit"
- Adaptive delays automatically increase
- Reduce `BATCH_SIZE` or increase `MAX_DELAY`
- Check Google Sheets API quota

### 📊 "Sheet not updating"
- Verify `GOOGLE_SHEET_URL` is correct
- Check sheet permissions
- Review Dashboard sheet for error logs

---

## 📝 Logs & Monitoring

### Local Logs (Enhanced Display)
```
======================================================================
🌐 DamaDam Online Bot v3.2.1 (Smart Scheduling + Quota Aware)
======================================================================

======================================================================
📊 RUN #1 | Started: 16:07:27
======================================================================
[16:07:27] 🔐 Checking for saved cookies...
[16:07:29] ✅ Login via cookies successful
[16:07:50] 📋 Processing 64 users...
[16:07:53] [  1/64 | ETA 12m 34s] ALi.SM0KER
[16:07:54] 📍 Scraping: ALi.SM0KER
[16:07:57] ✅ Extracted: 🕺, Murree, Posts: 483
[16:08:03] [  2/64 | ETA 11m 42s] aliyan_786
...
[16:44:47] [57/64 | ETA  1m  1s] ShooNa_Mundaa
[16:44:47] ⚠️ Quota limit hit, skipping: ShooNa_Mundaa

======================================================================
✅ RUN #1 COMPLETED
======================================================================
📊 Results: 57 Success | 2 Failed | 5 Quota-Skipped | 0 Suspended
📈 Breakdown: 12 New | 38 Updated | 7 Unchanged

⏱️ Run took 37.2 min. Waiting 0.0 min before next run...
```

### Sheet Formatting

- **Font**: Courier New (monospace for better readability)
- **Headers**: Bold, orange background (#ff9900)
- **Body**: Normal, size 8
- **Rows**: Alternating light orange shade
- **Frozen**: Row 1 (headers)
- **Sorting**:
  - ProfilesOnline: By DATETIME SCRAP (newest first)
  - Dashboard: By Timestamp (newest first)
  - NickList: By Last Seen (newest first), then by Nick Name

### GitHub Actions
- View logs in **Actions → Workflow Run → Run Online Bot**
- Check Dashboard sheet for historical metrics
- Monitor quota usage in logs (⚠️ Quota limit messages)

---

## 🔄 Version History

| Version | Changes |
|---------|---------|
| **3.2.1** | Smart scheduling, no timeout cancellations, complete list processing |
| 3.2.0 | Adaptive delays, batch cooloff |
| 3.1.0 | Nick tracking, dashboard |
| 3.0.0 | Initial single-file release |

---

## 📄 License

MIT License - Feel free to use and modify!

---

## 💬 Support

For issues or questions:
1. Check the **Troubleshooting** section above
2. Review GitHub Actions logs
3. Check Dashboard sheet for run statistics
4. Open an issue on GitHub

---

**Made with ❤️ for DamaDam.pk community**
