#!/usr/bin/env python3
"""
DamaDam Online Bot - Single File v3.2.1
- Scrapes online users and writes to Google Sheets (ProfilesOnline)
- Inserts new/updated rows at Row 2
- Duplicate check by Nickname (Col B)
- Highlights changed cells (excluding D,E,K,O,Q,R)
- Adaptive delay to avoid Google API rate limits
"""

import os
import sys
import re
import time
import json
import random
from datetime import datetime, timedelta, timezone

# ------------ Selenium ------------
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# ------------ Google Sheets ------------
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound, APIError

# ------------ Configuration (Env) ------------
LOGIN_URL = "https://damadam.pk/login/"
HOME_URL = "https://damadam.pk/"
ONLINE_URL = "https://damadam.pk/online_kon/"
COOKIE_FILE = "damadam_cookies.pkl"

USERNAME = os.getenv('DAMADAM_USERNAME', '')
PASSWORD = os.getenv('DAMADAM_PASSWORD', '')
USERNAME_2 = os.getenv('DAMADAM_USERNAME_2', '')
PASSWORD_2 = os.getenv('DAMADAM_PASSWORD_2', '')
SHEET_URL = os.getenv('GOOGLE_SHEET_URL', '')
GOOGLE_CREDENTIALS_RAW = os.getenv('GOOGLE_CREDENTIALS_JSON', '')

MAX_PROFILES_PER_RUN = int(os.getenv('MAX_PROFILES_PER_RUN', '0'))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '10'))
MIN_DELAY = float(os.getenv('MIN_DELAY', '0.5'))
MAX_DELAY = float(os.getenv('MAX_DELAY', '0.7'))
PAGE_LOAD_TIMEOUT = int(os.getenv('PAGE_LOAD_TIMEOUT', '30'))
SHEET_WRITE_DELAY = float(os.getenv('SHEET_WRITE_DELAY', '1.0'))

COLUMN_ORDER = [
    "IMAGE", "NICK NAME", "TAGS", "LAST POST", "LAST POST TIME", "FRIEND", "CITY",
    "GENDER", "MARRIED", "AGE", "JOINED", "FOLLOWERS", "STATUS",
    "POSTS", "PROFILE LINK", "INTRO", "SOURCE", "DATETIME SCRAP"
]
COLUMN_TO_INDEX = {name: idx for idx, name in enumerate(COLUMN_ORDER)}
HIGHLIGHT_EXCLUDE_COLUMNS = {"LAST POST", "LAST POST TIME", "JOINED", "PROFILE LINK", "DATETIME SCRAP"}
LINK_COLUMNS = {"IMAGE", "LAST POST", "PROFILE LINK"}
ENABLE_CELL_HIGHLIGHT = False
SUSPENSION_INDICATORS = [
    "accounts suspend",
    "aik se zyada fake accounts",
    "abuse ya harassment",
    "kisi aur user ki identity apnana",
    "accounts suspend kiye",
]
NICK_LIST_SHEET = "NickList"
NICK_LIST_HEADERS = [
    "Nick Name",
    "Times Seen",
    "First Seen",
    "Last Seen",
]

# ------------ Helpers ------------

def get_pkt_time():
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)

def log_msg(msg):
    print(f"[{get_pkt_time().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def column_letter(col_idx: int) -> str:
    res = ""
    col_idx += 1
    while col_idx > 0:
        col_idx -= 1
        res = chr(col_idx % 26 + ord('A')) + res
        col_idx //= 26
    return res

def clean_data(v: str) -> str:
    if not v:
        return ""
    v = str(v).strip().replace('\xa0', ' ')
    bad = {"No city","Not set","[No Posts]","N/A","no city","not set","[no posts]","n/a","[No Post URL]","[Error]","no set","none","null","no age"}
    return "" if v in bad else re.sub(r"\s+"," ", v)

def convert_relative_date_to_absolute(text: str) -> str:
    if not text:
        return ""
    t = text.lower().strip()
    t = t.replace("mins","minutes").replace("min","minute").replace("secs","seconds").replace("sec","second").replace("hrs","hours").replace("hr","hour")
    m = re.search(r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago", t)
    if not m:
        return text
    amt = int(m.group(1)); unit = m.group(2)
    delta_map = {"second":1,"minute":60,"hour":3600,"day":86400,"week":604800,"month":2592000,"year":31536000}
    if unit in delta_map:
        dt = get_pkt_time() - timedelta(seconds=amt*delta_map[unit])
        return dt.strftime("%d-%b-%y")
    return text

def detect_suspension_reason(page: str) -> str | None:
    if not page:
        return None
    lower = page.lower()
    for indicator in SUSPENSION_INDICATORS:
        if indicator in lower:
            return indicator
    return None

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = str(text).strip().replace('\xa0',' ').replace('\n',' ')
    return re.sub(r"\s+"," ", text).strip()

def parse_post_timestamp(text:str)->str:
    return convert_relative_date_to_absolute(text)

def to_absolute_url(href:str)->str:
    if not href:
        return ""
    href=href.strip()
    if href.startswith('/'):
        return f"https://damadam.pk{href}"
    if not href.startswith('http'):
        return f"https://damadam.pk/{href}"
    return href

def get_friend_status(driver)->str:
    try:
        page_source=driver.page_source.lower()
        if 'action="/follow/remove/"' in page_source or 'unfollow.svg' in page_source:
            return "Yes"
        if 'follow.svg' in page_source and 'unfollow' not in page_source:
            return "No"
        return ""
    except Exception:
        return ""

def calculate_eta(processed:int, total:int, start_ts:float)->str:
    if processed==0:
        return "Calculating..."
    elapsed=time.time()-start_ts
    rate=processed/elapsed if elapsed>0 else 0
    remaining=total-processed
    eta=remaining/rate if rate>0 else 0
    if eta<60:
        return f"{int(eta)}s"
    if eta<3600:
        return f"{int(eta//60)}m {int(eta%60)}s"
    hrs=int(eta//3600); mins=int((eta%3600)//60)
    return f"{hrs}h {mins}m"

def extract_text_comment_url(href:str)->str:
    m=re.search(r'/comments/text/(\d+)/', href or '')
    if m:
        return to_absolute_url(f"/comments/text/{m.group(1)}/").rstrip('/')
    return to_absolute_url(href or '')

def extract_image_comment_url(href:str)->str:
    m=re.search(r'/comments/image/(\d+)/', href or '')
    if m:
        return to_absolute_url(f"/content/{m.group(1)}/g/")
    return to_absolute_url(href or '')

def scrape_recent_post(driver, nickname:str)->dict:
    post_url=f"https://damadam.pk/profile/public/{nickname}"
    try:
        driver.get(post_url)
        try:
            WebDriverWait(driver,5).until(EC.presence_of_element_located((By.CSS_SELECTOR,"article.mbl")))
        except TimeoutException:
            return {'LPOST':'','LDATE-TIME':''}

        recent_post=driver.find_element(By.CSS_SELECTOR,"article.mbl")
        post_data={'LPOST':'','LDATE-TIME':''}

        url_selectors=[
            ("a[href*='/content/']", lambda h: to_absolute_url(h)),
            ("a[href*='/comments/text/']", extract_text_comment_url),
            ("a[href*='/comments/image/']", extract_image_comment_url),
        ]
        for selector, formatter in url_selectors:
            try:
                link=recent_post.find_element(By.CSS_SELECTOR, selector)
                href=link.get_attribute('href')
                if href:
                    formatted=formatter(href)
                    if formatted:
                        post_data['LPOST']=formatted
                        break
            except Exception:
                continue

        time_selectors=["span[itemprop='datePublished']","time[itemprop='datePublished']","span.cxs.cgy","time"]
        for sel in time_selectors:
            try:
                time_elem=recent_post.find_element(By.CSS_SELECTOR, sel)
                if time_elem.text.strip():
                    post_data['LDATE-TIME']=parse_post_timestamp(time_elem.text.strip())
                    break
            except Exception:
                continue
        return post_data
    except Exception:
        return {'LPOST':'','LDATE-TIME':''}

# ------------ Adaptive Delay ------------
class AdaptiveDelay:
    def __init__(self, mn, mx):
        self.base_min = mn; self.base_max = mx
        self.min_delay = mn; self.max_delay = mx
        self.hits = 0; self.last = time.time()
    def on_success(self):
        if self.hits: self.hits -= 1
        if time.time()-self.last > 10:
            self.min_delay = max(self.base_min, self.min_delay*0.95)
            self.max_delay = max(self.base_max, self.max_delay*0.95)
            self.last = time.time()
    def on_rate_limit(self):
        self.hits += 1
        factor = 1 + min(0.2*self.hits, 1.0)
        self.min_delay = min(3.0, self.min_delay*factor)
        self.max_delay = min(6.0, self.max_delay*factor)
    def on_batch(self):
        self.min_delay = min(3.0, max(self.base_min, self.min_delay*1.1))
        self.max_delay = min(6.0, max(self.base_max, self.max_delay*1.1))
    def sleep(self):
        time.sleep(random.uniform(self.min_delay, self.max_delay))

adaptive = AdaptiveDelay(MIN_DELAY, MAX_DELAY)

# ------------ Browser ------------

def setup_browser():
    try:
        log_msg("Setting up Chrome...")
        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option('excludeSwitches', ['enable-automation'])
        opts.add_experimental_option('useAutomationExtension', False)
        opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.execute_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        log_msg("Chrome ready")
        return driver
    except Exception as e:
        log_msg(f"Browser error: {e}")
        return None

def save_cookies(driver):
    try:
        import pickle
        with open(COOKIE_FILE,'wb') as f:
            pickle.dump(driver.get_cookies(), f)
        log_msg("Cookies saved")
    except Exception as e:
        log_msg(f"Cookie save failed: {e}")

def load_cookies(driver):
    try:
        import pickle, os
        if not os.path.exists(COOKIE_FILE):
            return False
        with open(COOKIE_FILE,'rb') as f:
            cookies = pickle.load(f)
        for c in cookies:
            try: driver.add_cookie(c)
            except: pass
        log_msg(f"Loaded {len(cookies)} cookies")
        return True
    except Exception as e:
        log_msg(f"Cookie load failed: {e}")
        return False

def login(driver) -> bool:
    try:
        driver.get(HOME_URL); time.sleep(2)
        if load_cookies(driver):
            driver.refresh(); time.sleep(3)
            if 'login' not in driver.current_url.lower():
                log_msg("Login via cookies")
                return True
        driver.get(LOGIN_URL); time.sleep(3)
        for label, u, p in [("Account 1", USERNAME, PASSWORD), ("Account 2", USERNAME_2, PASSWORD_2)]:
            if not u or not p: continue
            try:
                nick = WebDriverWait(driver,8).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#nick, input[name='nick']")))
                try:
                    passf = driver.find_element(By.CSS_SELECTOR, "#pass, input[name='pass']")
                except:
                    passf = WebDriverWait(driver,8).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
                btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], form button")
                nick.clear(); nick.send_keys(u); time.sleep(0.5)
                passf.clear(); passf.send_keys(p); time.sleep(0.5)
                btn.click(); time.sleep(4)
                if 'login' not in driver.current_url.lower():
                    log_msg(f"{label} login OK")
                    save_cookies(driver)
                    return True
            except Exception:
                continue
        return False
    except Exception as e:
        log_msg(f"Login error: {e}")
        return False

# ------------ Google Sheets ------------

def gsheets_client():
    if not SHEET_URL:
        print("❌ GOOGLE_SHEET_URL is not set."); sys.exit(1)
    scope = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    gac_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS','').strip()
    try:
        if gac_path and os.path.exists(gac_path):
            cred = Credentials.from_service_account_file(gac_path, scopes=scope)
        else:
            if not GOOGLE_CREDENTIALS_RAW:
                print("❌ GOOGLE_SHEET_URL is set but GOOGLE_CREDENTIALS_JSON is missing.")
                sys.exit(1)
            cred = Credentials.from_service_account_info(json.loads(GOOGLE_CREDENTIALS_RAW), scopes=scope)
        return gspread.authorize(cred)
    except Exception as e:
        print(f"❌ Google auth failed: {e}"); sys.exit(1)

class Sheets:
    def __init__(self, client):
        self.client = client
        self.tags_mapping = {}
        self.existing = {}
        self.nick_list_existing = {}
        self.nick_list_next_row = 2
        self.ss = client.open_by_url(SHEET_URL)
        self.ws = self._get_or_create("ProfilesOnline", cols=len(COLUMN_ORDER))
        self.tags_sheet = self._get_sheet_if_exists("Tags")
        # Ensure headers exist for ProfilesOnline
        try:
            values = self.ws.get_all_values()
            if not values or not values[0] or all(not c for c in values[0]):
                log_msg("Initializing ProfilesOnline headers...")
                self.ws.append_row(COLUMN_ORDER)
                try: self.ws.freeze(rows=1)
                except: pass
        except Exception as e:
            log_msg(f"Header init failed: {e}")
        # Dashboard worksheet
        try:
            self.dashboard = self._get_or_create("Dashboard", cols=11)
            dvals = self.dashboard.get_all_values()
            expected = ["Run#","Timestamp","Profiles","Success","Failed","New","Updated","Unchanged","Trigger","Start","End"]
            if not dvals or dvals[0] != expected:
                self.dashboard.clear()
                self.dashboard.append_row(expected)
        except Exception as e:
            log_msg(f"Dashboard setup failed: {e}")
        self._format()
        self._load_existing()
        self._load_tags_mapping()
        self._ensure_nick_list()

    def _get_or_create(self, name, cols=20, rows=1000):
        try:
            return self.ss.worksheet(name)
        except WorksheetNotFound:
            return self.ss.add_worksheet(title=name, rows=rows, cols=cols)

    def _get_sheet_if_exists(self, name):
        try:
            return self.ss.worksheet(name)
        except WorksheetNotFound:
            log_msg(f"{name} sheet not found, skipping optional features")
            return None

    def _apply_banding(self, sheet, end_col, start_row=1):
        try:
            end_col = max(end_col, 1)
            req = {
                "addBanding": {
                    "bandedRange": {
                        "range": {
                            "sheetId": sheet.id,
                            "startRowIndex": start_row,
                            "startColumnIndex": 0,
                            "endColumnIndex": end_col,
                        },
                        "rowProperties": {
                            "headerColor": {"red": 1.0, "green": 0.6, "blue": 0.0},
                            "firstBandColor": {"red": 1.0, "green": 0.98, "blue": 0.94},
                            "secondBandColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        },
                    }
                }
            }
            self.ss.batch_update({"requests": [req]})
        except APIError as e:
            message = str(e)
            if "already has alternating background colors" in message:
                log_msg(f"Banding already applied on {sheet.title}; skipping reapply")
            else:
                log_msg(f"Banding failed: {e}")

    def _format(self):
        try:
            self.ws.format("A:R", {"backgroundColor":{"red":1,"green":1,"blue":1},"textFormat":{"fontFamily":"Bona Nova SC","fontSize":8,"bold":False}})
            self.ws.format("A1:R1", {"textFormat":{"bold":False,"fontSize":9,"fontFamily":"Bona Nova SC"},"horizontalAlignment":"CENTER","backgroundColor":{"red":1.0,"green":0.6,"blue":0.0}})
            self._apply_banding(self.ws, len(COLUMN_ORDER), start_row=1)
        except Exception as e:
            log_msg(f"Format failed: {e}")
        try:
            self.dashboard.format("A:K", {"textFormat":{"fontFamily":"Bona Nova SC","fontSize":8,"bold":False}})
            self.dashboard.format("A1:K1", {"textFormat":{"bold":True,"fontSize":9,"fontFamily":"Bona Nova SC"},"horizontalAlignment":"CENTER","backgroundColor":{"red":1.0,"green":0.6,"blue":0.0}})
            self._apply_banding(self.dashboard, self.dashboard.col_count, start_row=1)
        except Exception as e:
            log_msg(f"Dashboard format failed: {e}")

    def _load_existing(self):
        try:
            self.existing = {}
            rows = self.ws.get_all_values()[1:]
            for i, r in enumerate(rows, start=2):
                if len(r)>1 and r[1].strip():
                    self.existing[r[1].strip().lower()] = {'row': i, 'data': r}
            log_msg(f"Loaded {len(self.existing)} existing")
        except Exception as e:
            log_msg(f"Load existing failed: {e}")

    def _load_tags_mapping(self):
        self.tags_mapping = {}
        if not self.tags_sheet:
            return
        try:
            all_values = self.tags_sheet.get_all_values()
            if not all_values or len(all_values) < 2:
                return
            headers = all_values[0]
            for col_idx, header in enumerate(headers):
                tag_name = clean_data(header)
                if not tag_name:
                    continue
                for row in all_values[1:]:
                    if col_idx < len(row):
                        nickname = row[col_idx].strip()
                        if nickname:
                            key = nickname.lower()
                            if key in self.tags_mapping:
                                if tag_name not in self.tags_mapping[key]:
                                    self.tags_mapping[key] += f", {tag_name}"
                            else:
                                self.tags_mapping[key] = tag_name
            log_msg(f"Loaded {len(self.tags_mapping)} tags")
        except Exception as e:
            log_msg(f"Tags load failed: {e}")

    def _ensure_nick_list(self):
        try:
            self.nick_list_ws = self._get_or_create(NICK_LIST_SHEET, cols=len(NICK_LIST_HEADERS))
            values = self.nick_list_ws.get_all_values()
            headers_present = values[0] if values else []
            if headers_present[: len(NICK_LIST_HEADERS)] != NICK_LIST_HEADERS:
                self.nick_list_ws.clear()
                self.nick_list_ws.append_row(NICK_LIST_HEADERS)
                values = self.nick_list_ws.get_all_values()
            self.nick_list_next_row = len(values) + 1 if values else 2
        except Exception as e:
            log_msg(f"Nick list init failed: {e}")
            self.nick_list_ws = None
            return
        self._load_nick_list()

    def _load_nick_list(self):
        if not getattr(self, 'nick_list_ws', None):
            return
        self.nick_list_existing = {}
        try:
            values = self.nick_list_ws.get_all_values()
            for idx, row in enumerate(values[1:], start=2):
                nickname = (row[0] if len(row) > 0 else '').strip()
                if not nickname:
                    continue
                times_seen = row[1].strip() if len(row) > 1 else ""
                first_seen = row[2].strip() if len(row) > 2 else ""
                last_seen = row[3].strip() if len(row) > 3 else ""
                try:
                    times_val = int(times_seen)
                except Exception:
                    times_val = 0
                self.nick_list_existing[nickname.lower()] = {
                    "row": idx,
                    "times": times_val,
                    "first": first_seen,
                    "last": last_seen,
                }
            self.nick_list_next_row = len(values) + 1 if values else 2
        except Exception as e:
            log_msg(f"Nick list load failed: {e}")

    def record_nick_seen(self, nickname: str, seen_at: datetime | None = None):
        if not nickname:
            return
        if not getattr(self, 'nick_list_ws', None):
            return
        seen_at = seen_at or get_pkt_time()
        ts = seen_at.strftime("%d-%b-%y %I:%M %p")
        key = nickname.strip().lower()
        if not key:
            return
        entry = self.nick_list_existing.get(key)
        if entry:
            times = entry['times'] + 1
            first_seen = entry['first'] or ts
            last_seen = ts
            row = entry['row']
            try:
                self.nick_list_ws.update(f"A{row}:D{row}", [[nickname, str(times), first_seen, last_seen]], value_input_option='USER_ENTERED')
                time.sleep(SHEET_WRITE_DELAY)
            except Exception as e:
                log_msg(f"Nick list update failed for {nickname}: {e}")
                return
            entry['times'] = times
            entry['last'] = last_seen
        else:
            first_seen = ts
            last_seen = ts
            row = self.nick_list_next_row
            try:
                self.nick_list_ws.append_row([nickname, "1", first_seen, last_seen])
                time.sleep(SHEET_WRITE_DELAY)
            except Exception as e:
                log_msg(f"Nick list append failed for {nickname}: {e}")
                return
            self.nick_list_existing[key] = {
                "row": row,
                "times": 1,
                "first": first_seen,
                "last": last_seen,
            }
            self.nick_list_next_row += 1

    def update_dashboard(self, metrics: dict):
        try:
            row = [
                metrics.get("Run Number", 1),
                metrics.get("Last Run", get_pkt_time().strftime("%d-%b-%y %I:%M %p")),
                metrics.get("Profiles Processed", 0),
                metrics.get("Success", 0),
                metrics.get("Failed", 0),
                metrics.get("New Profiles", 0),
                metrics.get("Updated Profiles", 0),
                metrics.get("Unchanged Profiles", 0),
                metrics.get("Trigger", os.getenv('GITHUB_EVENT_NAME','manual')),
                metrics.get("Start", get_pkt_time().strftime("%d-%b-%y %I:%M %p")),
                metrics.get("End", get_pkt_time().strftime("%d-%b-%y %I:%M %p")),
            ]
            self.dashboard.append_row(row)
        except Exception as e:
            log_msg(f"Dashboard update failed: {e}")

    def _update_links(self, row_idx, data):
        for col in LINK_COLUMNS:
            val = data.get(col)
            if not val: continue
            cidx = COLUMN_TO_INDEX[col]
            cell = f"{column_letter(cidx)}{row_idx}"
            if col == "IMAGE":
                formula = f'=IMAGE("{val}", 4, 50, 50)'
            elif col == "LAST POST":
                formula = f'=HYPERLINK("{val}", "Post")'
            else:
                formula = f'=HYPERLINK("{val}", "Profile")'
            self.ws.update(values=[[formula]], range_name=cell, value_input_option='USER_ENTERED')
            time.sleep(SHEET_WRITE_DELAY)

    def _highlight(self, row_idx, indices):
        for idx in indices:
            rng = f"{column_letter(idx)}{row_idx}:{column_letter(idx)}{row_idx}"
            self.ws.format(rng, {"backgroundColor": {"red":1.0,"green":0.93,"blue":0.85}})
            time.sleep(SHEET_WRITE_DELAY)

    def _add_notes(self, row_idx, indices, before, new_vals):
        if not indices: return
        reqs=[]
        for idx in indices:
            note = f"Before: {before.get(COLUMN_ORDER[idx], '')}\nAfter: {new_vals[idx]}"
            reqs.append({"updateCells":{ "range":{"sheetId": self.ws.id, "startRowIndex":row_idx-1, "endRowIndex":row_idx, "startColumnIndex":idx, "endColumnIndex":idx+1}, "rows":[{"values":[{"note":note}]}], "fields":"note" }})
        if reqs:
            self.ss.batch_update({"requests": reqs})

    def write_profile(self, profile: dict):
        nickname = (profile.get("NICK NAME") or "").strip()
        if not nickname:
            return {"status":"error","error":"Missing nickname","changed_fields":[]}
        # Normalize
        if profile.get("LAST POST TIME"):
            profile["LAST POST TIME"] = convert_relative_date_to_absolute(profile["LAST POST TIME"])
        profile["DATETIME SCRAP"] = get_pkt_time().strftime("%d-%b-%y %I:%M %p")
        nickname_lower = nickname.lower()
        tags_value = self.tags_mapping.get(nickname_lower)
        if tags_value:
            profile["TAGS"] = tags_value
        # Row values
        row_values = []
        for c in COLUMN_ORDER:
            if c == "IMAGE":
                v = ""
            elif c == "PROFILE LINK":
                v = "Profile" if profile.get(c) else ""
            elif c == "LAST POST":
                v = "Post" if profile.get(c) else ""
            else:
                v = clean_data(profile.get(c, ""))
            row_values.append(v)
        key = nickname_lower
        existing = self.existing.get(key)
        if existing:
            before = {COLUMN_ORDER[i]: (existing['data'][i] if i < len(existing['data']) else "") for i in range(len(COLUMN_ORDER))}
            changed = []
            for i, col in enumerate(COLUMN_ORDER):
                if col in HIGHLIGHT_EXCLUDE_COLUMNS: continue
                old = before.get(col, "") or ""; new = row_values[i] or ""
                if old != new: changed.append(i)
            # Insert at row 2
            self.ws.insert_row(row_values, 2); self._update_links(2, profile)
            if changed:
                if ENABLE_CELL_HIGHLIGHT:
                    self._highlight(2, changed)
                self._add_notes(2, changed, before, row_values)
            # Delete old row (shift by +1 due to the insert)
            try:
                old_row = existing['row'] + 1 if existing['row'] >= 2 else 3
                self.ws.delete_rows(old_row)
            except Exception as e:
                log_msg(f"Old row delete failed: {e}")
            self.existing[key] = {'row': 2, 'data': row_values}
            status = "updated" if changed else "unchanged"
            result = {"status": status, "changed_fields": [COLUMN_ORDER[i] for i in changed]}
        else:
            self.ws.insert_row(row_values, 2); self._update_links(2, profile)
            self.existing[key] = {'row': 2, 'data': row_values}
            result = {"status":"new","changed_fields": list(COLUMN_ORDER)}
        time.sleep(SHEET_WRITE_DELAY)
        return result

# ------------ Scraping ------------

def fetch_online_nicknames(driver):
    log_msg("Fetching online users...")
    driver.get(ONLINE_URL); time.sleep(2)
    names = []
    try:
        items = driver.find_elements(By.CSS_SELECTOR, "li.mbl.cl.sp b")
        for b in items:
            nick = (b.text or '').strip()
            if nick and len(nick) >= 3 and any(ch.isalpha() for ch in nick):
                names.append(nick)
    except Exception:
        pass
    if not names:
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/users/']")
        for a in links:
            href = a.get_attribute('href') or ''
            if '/users/' in href:
                nick = href.split('/users/')[-1].rstrip('/')
                if nick and nick not in names and any(ch.isalpha() for ch in nick):
                    names.append(nick)
    log_msg(f"Found {len(names)} online")
    return names

def scrape_profile(driver, nickname: str) -> dict | None:
    url = f"https://damadam.pk/users/{nickname}/"
    try:
        log_msg(f"📍 Scraping: {nickname}")
        driver.get(url)
        WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CSS_SELECTOR,"h1.cxl.clb.lsp")))

        page_source = driver.page_source
        now = get_pkt_time()
        suspend_reason = detect_suspension_reason(page_source)
        data = {
            "IMAGE":"",
            "NICK NAME": nickname,
            "TAGS":"",
            "LAST POST":"",
            "LAST POST TIME":"",
            "FRIEND":"",
            "CITY":"",
            "GENDER":"",
            "MARRIED":"",
            "AGE":"",
            "JOINED":"",
            "FOLLOWERS":"",
            "STATUS":"",
            "POSTS":"",
            "PROFILE LINK": url.rstrip('/'),
            "INTRO":"",
            "SOURCE":"Online",
            "DATETIME SCRAP": now.strftime("%d-%b-%y %I:%M %p"),
        }

        if suspend_reason:
            data['STATUS'] = "Suspended"
            data['INTRO'] = f"Suspended: {suspend_reason}"[:250]
            data['SUSPENSION_REASON'] = suspend_reason
            return data

        if 'account suspended' in page_source.lower():
            data['STATUS']="Suspended"
        elif 'background:tomato' in page_source or 'style="background:tomato"' in page_source.lower():
            data['STATUS']="Unverified"
        else:
            try:
                driver.find_element(By.CSS_SELECTOR,"div[style*='tomato']")
                data['STATUS']="Unverified"
            except Exception:
                data['STATUS']="Verified"

        data['FRIEND']=get_friend_status(driver)

        for sel in ["span.cl.sp.lsp.nos","span.cl",".ow span.nos"]:
            try:
                intro=driver.find_element(By.CSS_SELECTOR, sel)
                if intro.text.strip():
                    data['INTRO']=clean_text(intro.text)
                    break
            except Exception:
                pass

        fields={'City:':'CITY','Gender:':'GENDER','Married:':'MARRIED','Age:':'AGE','Joined:':'JOINED'}
        for label,key in fields.items():
            try:
                elem=driver.find_element(By.XPATH,f"//b[contains(text(), '{label}')]/following-sibling::span[1]")
                value=elem.text.strip()
                if not value:
                    continue
                if key=='JOINED':
                    data[key]=convert_relative_date_to_absolute(value)
                elif key=='GENDER':
                    low=value.lower()
                    data[key]="💃" if low=='female' else "🕺" if low=='male' else value
                elif key=='MARRIED':
                    low=value.lower()
                    if low in {'yes','married'}:
                        data[key]="💍"
                    elif low in {'no','single','unmarried'}:
                        data[key]="❎"
                    else:
                        data[key]=value
                else:
                    data[key]=clean_data(value)
            except Exception:
                continue

        for sel in ["span.cl.sp.clb",".cl.sp.clb"]:
            try:
                followers=driver.find_element(By.CSS_SELECTOR, sel)
                match=re.search(r'(\d+)', followers.text)
                if match:
                    data['FOLLOWERS']=match.group(1)
                    break
            except Exception:
                pass

        for sel in ["a[href*='/profile/public/'] button div:first-child","a[href*='/profile/public/'] button div"]:
            try:
                posts=driver.find_element(By.CSS_SELECTOR, sel)
                match=re.search(r'(\d+)', posts.text)
                if match:
                    data['POSTS']=match.group(1)
                    break
            except Exception:
                pass

        for sel in ["img[src*='avatar-imgs']","img[src*='avatar']","div[style*='whitesmoke'] img[src*='cloudfront.net']"]:
            try:
                img=driver.find_element(By.CSS_SELECTOR, sel)
                src=img.get_attribute('src')
                if src and ('avatar' in src or 'cloudfront.net' in src):
                    data['IMAGE']=src.replace('/thumbnail/','/')
                    break
            except Exception:
                pass

        if data.get('POSTS') and data['POSTS']!='0':
            time.sleep(1)
            post_data=scrape_recent_post(driver, nickname)
            data['LAST POST']=clean_data(post_data.get('LPOST',''))
            data['LAST POST TIME']=post_data.get('LDATE-TIME','')

        log_msg(f"✅ Extracted: {data['GENDER']}, {data['CITY']}, Posts: {data['POSTS']}")
        return data
    except TimeoutException:
        log_msg(f"⚠️ Timeout while scraping {nickname}")
        return None
    except WebDriverException:
        log_msg(f"⚠️ Browser issue while scraping {nickname}")
        return None
    except Exception as e:
        log_msg(f"❌ Error scraping {nickname}: {str(e)[:60]}")
        return None

# ------------ Main with Smart Scheduling ------------

def main():
    print("\n" + "="*60)
    print("🌐 DamaDam Online Bot v3.2.1 (Smart Scheduling)")
    print("="*60)

    if not USERNAME or not PASSWORD:
        print("❌ Missing DAMADAM_USERNAME / DAMADAM_PASSWORD"); sys.exit(1)
    
    RUN_INTERVAL = 15 * 60  # 15 minutes in seconds
    
    while True:
        run_start_time = time.time()
        run_started_dt = get_pkt_time()
        
        try:
            client = gsheets_client()
            sheets = Sheets(client)

            driver = setup_browser()
            if not driver:
                print("❌ Browser setup failed"); sys.exit(1)
            try:
                if not login(driver):
                    print("❌ Login failed"); driver.quit(); sys.exit(1)
                names = fetch_online_nicknames(driver)
                log_msg(f"Processing {len(names)} users...")
                # Always process the complete list (ignore MAX_PROFILES_PER_RUN)
                success = failed = suspended_count = 0
                run_stats = {"new":0, "updated":0, "unchanged":0}
                start_time = time.time()
                trigger_type = "Scheduled" if os.getenv('GITHUB_EVENT_NAME','').lower()=='schedule' else "Manual"
                for i, nick in enumerate(names, 1):
                    eta = calculate_eta(i-1, len(names), start_time)
                    log_msg(f"[{i}/{len(names)} | ETA {eta}] {nick}")
                    sheets.record_nick_seen(nick)
                    try:
                        prof = scrape_profile(driver, nick)
                        if not prof:
                            raise RuntimeError("Profile scrape failed")
                        suspend_reason = prof.get("SUSPENSION_REASON")
                        if suspend_reason:
                            sheets.write_profile(prof)
                            suspended_count += 1
                            log_msg(f"⚠️ {nick} skipped (suspended: {suspend_reason})")
                            continue
                        result = sheets.write_profile(prof)
                        status = result.get("status","error") if result else "error"
                        if status in {"new","updated","unchanged"}:
                            success += 1
                            run_stats[status] += 1
                        else:
                            raise RuntimeError(result.get("error","Write failed") if result else "Write failed")
                    except Exception as e:
                        failed += 1
                        log_msg(f"Write error: {e}")
                    if BATCH_SIZE > 0 and i % BATCH_SIZE == 0 and i < len(names):
                        log_msg("Batch cool-off"); adaptive.on_batch(); time.sleep(3)
                    adaptive.sleep()
                print("\n✅ Run completed")
                # Dashboard update
                sheets.update_dashboard({
                    "Run Number": 1,
                    "Last Run": get_pkt_time().strftime("%d-%b-%y %I:%M %p"),
                    "Profiles Processed": len(names),
                    "Success": success,
                    "Failed": failed,
                    "New Profiles": run_stats.get('new',0),
                    "Updated Profiles": run_stats.get('updated',0),
                    "Unchanged Profiles": run_stats.get('unchanged',0),
                    "Trigger": trigger_type,
                    "Start": run_started_dt.strftime("%d-%b-%y %I:%M %p"),
                    "End": get_pkt_time().strftime("%d-%b-%y %I:%M %p"),
                })
                if suspended_count:
                    print(f"   ⚠️ Suspended skipped: {suspended_count}")
            finally:
                try: driver.quit()
                except: pass
        except Exception as e:
            log_msg(f"❌ Run failed: {e}")
        
        # Smart scheduling: wait for next run
        elapsed = time.time() - run_start_time
        if elapsed >= RUN_INTERVAL:
            log_msg(f"⏱️ Run took {elapsed:.0f}s (> 15min). Starting next run immediately...")
            continue
        else:
            wait_time = RUN_INTERVAL - elapsed
            log_msg(f"⏱️ Run took {elapsed:.0f}s. Waiting {wait_time:.0f}s before next run...")
            time.sleep(wait_time)

if __name__ == "__main__":
    main()
