import requests
import re
import urllib3
import time
import threading
import random
import os
import sys
from urllib.parse import urlparse, parse_qs, urljoin
from datetime import datetime, date

# SSL သတိပေးချက်များကို ပိတ်ခြင်း
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===============================
# PREMIUM COLOR & STYLE SYSTEM
# ===============================
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
WHITE = "\033[97m"
RESET = "\033[0m"

# ===============================
# CONFIG & GLOBALS
# ===============================
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1hQIA31FeBIDKXfmyIv8UjDk-ixQEseDy-n7p9oFXphk/export?format=csv"
LOCAL_KEYS_FILE = os.path.expanduser("~/.ruijie_approved_keys.txt")

PING_THREADS = 5
MIN_INTERVAL = 0.1
MAX_INTERVAL = 0.3
DEBUG = False

stop_event = threading.Event()
current_auth_link = None
active_threads = []
thread_lock = threading.Lock()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def log_status(icon, msg, color=WHITE, end="\n"):
    """Premium Status Logger"""
    sys.stdout.write(f"\r{BOLD}{color}[ {icon} ] {msg}{RESET}{' ' * 10}{end}")
    sys.stdout.flush()

# ===============================
# KEY APPROVAL SYSTEM
# ===============================
def get_system_key():
    try: uid = os.geteuid()
    except AttributeError: uid = 1000
    try: username = os.getlogin()
    except: username = os.environ.get('USER', 'unknown')
    return f"{uid}{username}"

def fetch_authorized_keys_with_expiry():
    keys_data = {}
    try:
        response = requests.get(SHEET_CSV_URL, timeout=10)
        if response.status_code == 200:
            for line in response.text.strip().split('\n'):
                line = line.strip()
                if line and not any(x in line.lower() for x in ['keys', 'username']):
                    parts = line.split(',')
                    if len(parts) >= 1:
                        key = parts[0].strip().strip('"')
                        expiry = parts[2].strip().strip('"') if len(parts) > 2 else ""
                        keys_data[key] = expiry
            with open(LOCAL_KEYS_FILE, 'w') as f:
                for k, v in keys_data.items():
                    f.write(f"{k},{v}\n")
            return keys_data
    except:
        pass
    
    if os.path.exists(LOCAL_KEYS_FILE):
        try:
            with open(LOCAL_KEYS_FILE, 'r') as f:
                for line in f:
                    p = line.strip().split(',')
                    if len(p) >= 1: keys_data[p[0]] = p[1] if len(p) > 1 else ""
        except: pass
    return keys_data

def display_premium_ui(system_key, status, expiry, days_left, status_color):
    """Rounded Box ဖြင့် Premium UI ပြသခြင်း"""
    width = 56
    print(f"\n{CYAN}{BOLD}╭{'─' * (width-2)}╮{RESET}")
    print(f"{CYAN}{BOLD}│{RESET}{BOLD}                 RUIJIE TURBO ENGINE                  {CYAN}{BOLD}│{RESET}")
    print(f"{CYAN}{BOLD}│{RESET}                v2.0 • Premium Edition                {CYAN}{BOLD}│{RESET}")
    print(f"{CYAN}{BOLD}├{'─' * (width-2)}┤{RESET}")
    print(f"{CYAN}{BOLD}│{RESET} ❖ SYSTEM INFORMATION                                 {CYAN}{BOLD}│{RESET}")
    print(f"{CYAN}{BOLD}│{RESET}                                                      {CYAN}{BOLD}│{RESET}")
    
    # Rows
    rows = [
        ("System Key", system_key, WHITE),
        ("License Status", f"[ {status} ]", status_color),
        ("Valid Until", expiry, WHITE),
        ("Remaining Days", days_left, status_color if days_left != "N/A" else WHITE)
    ]
    
    for label, value, color in rows:
        label_text = f"  • {label:14}: "
        val_text = str(value)
        padding = width - len(label_text) - len(val_text) - 2
        print(f"{CYAN}{BOLD}│{RESET}{label_text}{color}{val_text}{RESET}{' ' * padding}{CYAN}{BOLD}│{RESET}")
        
    print(f"{CYAN}{BOLD}╰{'─' * (width-2)}╯{RESET}\n")

def check_approval():
    clear_screen()
    log_status("⟳", "Fetching License Data from Cloud...", CYAN)
    
    system_key = get_system_key()
    authorized_keys_data = fetch_authorized_keys_with_expiry()
    
    status, expiry, days_left = "NOT FOUND", "N/A", "N/A"
    color = RED
    is_approved = False

    if system_key in authorized_keys_data:
        expiry_str = authorized_keys_data[system_key]
        if expiry_str:
            try:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                diff = (expiry_date - date.today()).days
                expiry = expiry_str
                
                if diff < 0:
                    status, days_left, color = "EXPIRED", "0 Days", RED
                else:
                    status, days_left, color, is_approved = "APPROVED", f"{diff} Days", GREEN, True
            except:
                status, color, is_approved = "APPROVED (Format Err)", YELLOW, True
        else:
            status, expiry, days_left, color, is_approved = "APPROVED", "LIFETIME", "∞", GREEN, True

    clear_screen()
    display_premium_ui(system_key, status, expiry, days_left, color)
    
    if not is_approved:
        if status == "EXPIRED":
            log_status("!", "သင့်၏ Key သက်တမ်းကုန်ဆုံးသွားပါပြီ။ ကျေးဇူးပြု၍ Admin ဆီသို့ ဆက်သွယ်ပါ။", YELLOW)
        else:
            log_status("!", "Admin ဆီမှ Approved ရယူပါ။", YELLOW)
        return False
    return True

# ===============================
# EXIT LISTENER (STOP FUNCTION)
# ===============================
def listen_for_exit():
    while not stop_event.is_set():
        try:
            input() 
            stop_event.set()
            print(f"\n\n{RED}{BOLD}[ ⏹ ] User Termination Requested. Shutting down...{RESET}")
            break
        except EOFError:
            break

# ===============================
# WORKER & ENGINE
# ===============================
def worker_loop():
    """Silent Worker - UI တွင် ဝင်မရေးပါ"""
    session = requests.Session()
    while not stop_event.is_set():
        with thread_lock:
            target = current_auth_link
        if target:
            try:
                session.get(target, timeout=5, verify=False)
            except: pass
        time.sleep(random.uniform(MIN_INTERVAL, MAX_INTERVAL))

def start_engine():
    global current_auth_link, active_threads
    
    print(f"{YELLOW}  [ Press {BOLD}ENTER{RESET}{YELLOW} at any time to gracefully terminate ]{RESET}\n")
    log_status("⚡", "Initializing Turbo Core...", MAGENTA)
    time.sleep(1)

    exit_thread = threading.Thread(target=listen_for_exit, daemon=True)
    exit_thread.start()

    for _ in range(PING_THREADS):
        t = threading.Thread(target=worker_loop, daemon=True)
        t.start()
        active_threads.append(t)

    while not stop_event.is_set():
        session = requests.Session()
        test_url = "http://connectivitycheck.gstatic.com/generate_204"
        try:
            # 1. Check active internet
            try:
                check_r = requests.get(test_url, timeout=5)
                if check_r.status_code == 204:
                    log_status("🌐", "Network Active. Standing by...", BLUE, end="")
                    with thread_lock: current_auth_link = None
                    for _ in range(10):
                        if stop_event.is_set(): break
                        time.sleep(0.5)
                    continue
            except: pass

            # 2. Portal Check
            log_status("🔍", "Scanning for Captive Portal...", YELLOW, end="")
            r = requests.get(test_url, allow_redirects=True, timeout=5)
            if r.url == test_url:
                time.sleep(2)
                continue

            portal_url = r.url
            log_status("➤", f"Portal Detected: {urlparse(portal_url).netloc}", MAGENTA)
            
            # 3. SID Extraction
            r1 = session.get(portal_url, verify=False, timeout=10)
            path_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", r1.text)
            next_url = urljoin(portal_url, path_match.group(1)) if path_match else portal_url
            r2 = session.get(next_url, verify=False, timeout=10)
            
            sid = parse_qs(urlparse(r2.url).query).get('sessionId', [None])[0]
            if not sid:
                sid_match = re.search(r'sessionId=([a-zA-Z0-9]+)', r2.text)
                sid = sid_match.group(1) if sid_match else None

            if sid:
                log_status("✓", f"Session Locked: {sid[:8]}...", GREEN)
                params = parse_qs(urlparse(portal_url).query)
                gw_addr = params.get('gw_address', ['192.168.60.1'])[0]
                gw_port = params.get('gw_port', ['2060'])[0]
                
                with thread_lock:
                    current_auth_link = f"http://{gw_addr}:{gw_port}/wifidog/auth?token={sid}"
                
                log_status("🚀", "Turbo Mode Active. Sending background pulses...", CYAN, end="")
                
                while not stop_event.is_set():
                    try:
                        if requests.get(test_url, timeout=5).status_code == 204:
                            print() # New line when escaping portal
                            time.sleep(2)
                            break
                        time.sleep(2)
                    except: break
            else:
                time.sleep(3)

        except Exception as e:
            if stop_event.is_set(): break
            log_status("✗", "Connection lost or retrying...", RED, end="")
            time.sleep(3)

    log_status("✓", "Engine successfully shut down.", GREEN)

if __name__ == "__main__":
    try:
        if check_approval():
            start_engine()
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        stop_event.set()
        print(f"\n{RED}{BOLD}[ ⏹ ] Force Quit (Ctrl+C). Exiting...{RESET}")
        sys.exit(0)