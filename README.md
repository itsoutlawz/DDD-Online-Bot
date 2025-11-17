# 🕸️ DamaDam Online Users Profile Scraper Bot
A fully automated **Python + Selenium bot** that logs into **DamaDam.pk**, scrapes **online users**, extracts their **full profile details**, and writes everything to **Google Sheets**, every 15 minutes — using **GitHub Actions**.

<p align="left">
  <img src="https://img.shields.io/badge/build-passing-brightgreen" />
  <img src="https://img.shields.io/badge/CI-GitHub%20Actions-blue" />
  <img src="https://img.shields.io/badge/language-Python%203.11-blue" />
  <img src="https://img.shields.io/badge/status-active-brightgreen" />
  <img src="https://img.shields.io/badge/version-v3.2.1-blueviolet" />
</p>

---

# 📌 Overview

This bot:

✔ Logs into **DamaDam** using 2 possible accounts  
✔ Scrapes **currently online users**  
✔ Visits every profile → extracts detailed info  
✔ Fetches **latest post URL + timestamp**  
✔ Writes data into **Google Sheets**  
✔ Maintains a **Dashboard** sheet  
✔ Highlights changed fields + adds comparison notes  
✔ Adaptive delays avoid API rate limits  
✔ Fully automated via **GitHub Actions (every 15 minutes)**  

Ye poora system **zero local hosting** ke saath, sirf GitHub se chal raha hota hai.

---

# 🚀 Key Features

### 🔹 1. Fully Automated  
15 min interval par GitHub Action run hota hai → scraper execute.

### 🔹 2. Intelligent Profile Updating  
- New rows → Row 2 par insert  
- Updated rows → replaced + highlighted  
- Unchanged rows → ignored  
- Duplicate check via **nickname**

### 🔹 3. Google Sheets Integration  
- Separate sheets created automatically:  
  - **ProfilesOnline**  
  - **Dashboard**  
  - (Optional) **Tags**

### 🔹 4. Browser Automation (Selenium + Chrome Headless)  
- Human-like delays  
- Cookie sessions for fast login  
- Auto-handles timeouts, missing elements, and invalid users

### 🔹 5. Smart Post Detection  
Latest post URL detect karta hai from:  
- Image posts  
- Text posts  
- Content posts  
- Comment posts  

---

# 🛠️ Tech Stack

| Component | Used |
|----------|------|
| Programming Language | Python 3.11 |
| Browser | Chrome Headless |
| Automation | Selenium WebDriver |
| Data Storage | Google Sheets |
| Auth | Service Account JSON |
| Scheduler | GitHub Actions |
| Parsing | Regex, Beautiful extraction |
| Dashboard | Auto-updated stats |

---

# 📂 Project Structure

📦 DDD-Online-Bot ┣ 📜 Scraper.py (Main logic) ┣ 📜 requirements.txt ┣ 📁 .github/workflows/ ┃ ┗ 📜 online-bot.yml ┗ 📜 README.md

---

# ⚙️ How It Works (Flow Diagram)

[GitHub Actions Trigger] | v Start Workflow (Cron/Manual) | v Setup Python + Chrome | v Login → Fetch Online Users → Loop Profiles → Scrape Details | v Write Data to Google Sheet | v Update Dashboard (New/Updated/Failed/etc.) | v Done

---

# 🔑 Environment Variables (Secrets)

GitHub → Repository → Settings → Secrets → Actions

Add these:

| Secret Name | Purpose |
|-------------|----------|
| `DAMADAM_USERNAME` | Login account #1 |
| `DAMADAM_PASSWORD` | Password #1 |
| `DAMADAM_USERNAME_2` | Login account #2 (optional fallback) |
| `DAMADAM_PASSWORD_2` | Password #2 |
| `GOOGLE_SHEET_URL` | Your Google Sheet link |
| `GOOGLE_CREDENTIALS_JSON` | Full JSON of service account |

---

# 📄 Full Workflow File (GitHub Actions)

```yaml
name: "DDD Online Bot"

on:
  schedule:
    - cron: '*/15 * * * *'

  workflow_dispatch:
    inputs:
      max_profiles:
        description: 'Max Profiles (0 = unlimited)'
        default: '0'
      batch_size:
        description: 'Batch Size'
        default: '10'

jobs:
  run-bot:
    runs-on: ubuntu-latest
    timeout-minutes: 14

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Setup Chrome
        uses: browser-actions/setup-chrome@v1
        with:
          chrome-version: stable

      - name: Setup Chromedriver
        uses: nanasess/setup-chromedriver@v2

      - name: Prepare Google Credentials (optional)
        env:
          GOOGLE_CREDENTIALS_JSON: ${{ secrets.GOOGLE_CREDENTIALS_JSON }}
          GOOGLE_SHEET_URL: ${{ secrets.GOOGLE_SHEET_URL }}
        run: |
          if [ -n "$GOOGLE_SHEET_URL" ]; then
            if [ -z "$GOOGLE_CREDENTIALS_JSON" ]; then
              echo "❌ Missing Google Credentials" && exit 1
            fi
            printf '%s' "$GOOGLE_CREDENTIALS_JSON" > google_credentials.json
            echo "GOOGLE_APPLICATION_CREDENTIALS=${{ github.workspace }}/google_credentials.json" >> $GITHUB_ENV
          fi

      - name: Run Online Bot
        env:
          DAMADAM_USERNAME: ${{ secrets.DAMADAM_USERNAME }}
          DAMADAM_PASSWORD: ${{ secrets.DAMADAM_PASSWORD }}
          DAMADAM_USERNAME_2: ${{ secrets.DAMADAM_USERNAME_2 }}
          DAMADAM_PASSWORD_2: ${{ secrets.DAMADAM_PASSWORD_2 }}
          GOOGLE_SHEET_URL: ${{ secrets.GOOGLE_SHEET_URL }}
          MAX_PROFILES_PER_RUN: ${{ github.event.inputs.max_profiles || '0' }}
          BATCH_SIZE: ${{ github.event.inputs.batch_size || '10' }}
          MIN_DELAY: '0.5'
          MAX_DELAY: '0.6'
          PAGE_LOAD_TIMEOUT: '30'
          SHEET_WRITE_DELAY: '1.1'
        run: |
          python Scraper.py


---

📒 Google Sheets Structure

Sheet 1 — ProfilesOnline

Columns auto-created:

IMAGE | NICK NAME | TAGS | LAST POST | LAST POST TIME | FRIEND | CITY | ...

Row 1 = Header (auto)
All new entries → inserted at Row 2.


---

Sheet 2 — Dashboard

Run# | Timestamp | Profiles | Success | Failed | New | Updated | Unchanged | Trigger | Start | End

Har run par ek row add hoti hai.


---

# 🧠 Advanced Features Explained

✔ Adaptive Delay System

Google Sheets API rate limit break na ho, isliye delay dynamically increase/reduce hota hai.

✔ Changed Fields Highlighter

If any profile data changed, cells may be highlighted + notes:

Before: old value
After: new value

✔ Cookie-Based Login

Fast login — no need to login every run.


---

🩺 Troubleshooting

Bot stops after a few profiles

Increase:

MIN_DELAY
MAX_DELAY

Google Sheet authentication error

Check:

Service Account email is added to Google Sheet → Editor access

JSON is correct


DamaDam login fails

Check:
env vars → spelling + quotes not needed.


---

📞 Support

Agar tumhein koi issue aaye, workflow optimize karna ho, ya new features chahiye — just message.


---

⭐ Credits

Developed by itsoutlawz
Automation design & documentation by ChatGPT (Nadeem Support Mode)
