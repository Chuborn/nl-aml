import os
import re
import time
import msvcrt
import requests
import json
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, List, Dict, Any

# Color Constants
ColorRed     = "\033[31m"
ColorGreen   = "\033[32m"
ColorYellow  = "\033[93m"
ColorBlue    = "\033[94m"
ColorMagenta = "\033[95m"
ColorCyan    = "\033[96m"
ColorWhite   = "\033[97m"
ColorGray    = "\033[90m"
ColorPurple  = "\033[35m"
ColorOrange  = "\033[33m"
ColorBold    = "\033[1m"
ColorReset   = "\033[0m"

BASE_URL = "https://notletters.com"

class NL_Checker:
    def __init__(self):
        self.results_dir = ""
        self.valid_file = ""
        self.ongoing_file = ""
        self.dead_file = ""
        self.error_file = ""
        self.ms_canceled_file = ""
        self.found_accounts = []
        self.total_checked = 0

    def setup_results(self):
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.results_dir = os.path.join("results", f"nl_{now}")
        self.mails_dir = os.path.join(self.results_dir, "mails")
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.mails_dir, exist_ok=True)
        self.valid_file = os.path.join(self.results_dir, "VALID.txt")
        self.ongoing_file = os.path.join(self.results_dir, "ONGOING.txt")
        self.ongoing_root_file = f"ongoing-nl-{now}.txt"
        self.ms_canceled_file = os.path.join(self.results_dir, "MS_CANCELED.txt")
        self.dead_file = os.path.join(self.results_dir, "DEAD.txt")
        self.error_file = os.path.join(self.results_dir, "ERROR.txt")

    def log_result(self, file_path, data):
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(data + "\n")

    def get_txt_files(self):
        return [f for f in os.listdir('.') if f.endswith('.txt')]

    def select_file(self):
        files = self.get_txt_files()
        if not files:
            print(f"{ColorRed}No .txt files found in the current directory.{ColorReset}")
            return None
        
        current_idx = 0
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"{ColorCyan}{ColorBold}NL CHECKER (NotLetters) - BY Chuborn{ColorReset}")
            print(f"{ColorGray}ltc1qnt9an3zncufvs2vcueuy5nh8q04s9l2q78svu7{ColorReset}\n")
            print("Select a file to extract emails from (Use arrows, Enter to select):")
            for i, f in enumerate(files):
                if i == current_idx:
                    print(f" {ColorGreen}> {f}{ColorReset}")
                else:
                    print(f"   {f}")
            
            key = msvcrt.getch()
            if key == b'\r': # Enter
                return files[current_idx]
            elif key == b'\xe0': # Special key
                key = msvcrt.getch()
                if key == b'H': # Up
                    current_idx = (current_idx - 1) % len(files)
                elif key == b'P': # Down
                    current_idx = (current_idx + 1) % len(files)

    def extract_emails(self, filename):
        # Flexible regex for email:password
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}'
        self.found_accounts = []
        format_detected = None
        
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line: continue

                # 1. SV2 Format Check
                if "login at mail.shulkerv2.xyz" in line:
                    # Pattern example: Nathchamp11@gmail.com:Alishachamp0 | radian022108@arrangementmail.ru:password - login at mail.shulkerv2.xyz
                    sv2_match = re.search(r'\|\s*(' + email_pattern + r'):([^\s|]+)\s*-\s*login at mail\.shulkerv2\.xyz', line)
                    if sv2_match:
                        self.found_accounts.append((line, sv2_match.group(1), sv2_match.group(2)))
                        format_detected = "SV2"
                        continue

                # 2. UKN Format Check (Generic 2 emails, use 2nd one)
                emails = re.findall(email_pattern, line)
                if len(emails) >= 2:
                    email2 = emails[1]
                    # Find password following the 2nd email
                    # We look for email2:password
                    ukn_pattern = re.escape(email2) + r':([^\s|]+)'
                    ukn_match = re.search(ukn_pattern, line)
                    if ukn_match:
                        self.found_accounts.append((line, email2, ukn_match.group(1)))
                        if not format_detected:
                            format_detected = "UKN"
                        continue

                # 3. Default Format (Current logic - fallback)
                match = re.search(r'(' + email_pattern + r'):([^\s|]+)', line)
                if match:
                    self.found_accounts.append((line, match.group(1), match.group(2)))
        
        return len(self.found_accounts), format_detected

    def check_account(self, full_line, email, password):
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
        })
        
        try:
            # 1. Login
            session.get(f"{BASE_URL}/email/login")
            
            login_data = {
                "email": email,
                "password": password
            }
            
            headers = {
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded",
                "origin": BASE_URL,
                "referer": f"{BASE_URL}/email/login",
                "x-sveltekit-action": "true"
            }
            
            r = session.post(
                f"{BASE_URL}/email/login?/login",
                data=login_data,
                headers=headers,
                allow_redirects=False,
                timeout=15
            )
            
            is_logged_in = False
            if r.status_code == 200:
                try:
                    response_data = r.json()
                    if response_data.get("type") == "redirect" and response_data.get("location") == "/email":
                        is_logged_in = True
                except:
                    pass

            if not is_logged_in:
                self.log_result(self.error_file, f"{full_line} | Reason: Login failed (Status {r.status_code})")
                print(f"{ColorGray}{email} -> LOGIN ERROR{ColorReset}")
                return

            # 2. Fetch Inbox
            headers = {
                "accept": "*/*",
                "origin": BASE_URL,
                "referer": f"{BASE_URL}/email",
                "x-sveltekit-action": "true"
            }
            
            params = {"page": 1, "search": ""}
            r = session.post(f"{BASE_URL}/email/get", params=params, headers=headers, timeout=15)
            
            if r.status_code != 200:
                self.log_result(self.error_file, f"{full_line} | Reason: Fetch inbox failed ({r.status_code})")
                print(f"{ColorGray}{email} -> INBOX ERROR{ColorReset}")
                return

            data = r.json()
            letters = data.get("letters", [])
            
            if not letters:
                self.log_result(self.error_file, f"{full_line} | Reason: No messages found")
                print(f"{ColorGray}{email} -> EMPTY{ColorReset}")
                return

            # 3. Fetch specific message content and categorize
            full_body_text = ""
            newest_timestamp = 0
            
            for letter in letters:
                msg_id = letter.get("id")
                timestamp = letter.get("date", 0)
                if timestamp > newest_timestamp:
                    newest_timestamp = timestamp
                
                # Content is already in the 'letter' dict
                letter_detail = letter.get("letter", {})
                subject = letter.get("subject", "No Subject")
                html_content = letter_detail.get("html", "")
                text_content = letter_detail.get("text", "")
                
                if html_content:
                    clean_text = re.sub(r'<[^>]+>', ' ', html_content)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                else:
                    clean_text = text_content or "(No content)"
                
                full_body_text += f"ID: {msg_id} | SUBJECT: {subject}\n"
                full_body_text += f"{clean_text}\n"
                full_body_text += "="*60 + "\n\n"

            # Save all mail content
            mail_save_path = os.path.join(self.mails_dir, f"{email}.txt")
            with open(mail_save_path, "w", encoding="utf-8") as mf:
                mf.write(full_body_text)

            # Categorize
            if "Good news! The waiting period you started 30 days ago" in full_body_text:
                self.log_result(self.valid_file, f"{full_line}")
                print(f"{ColorGreen}{email} -> VALID{ColorReset}")
            elif "has been canceled." in full_body_text:
                self.log_result(self.dead_file, f"{full_line}")
                print(f"{ColorRed}{email} -> DEAD{ColorReset}")
            elif len(letters) == 1:
                # Check if it's over 35 days old
                delta_days = (time.time() - newest_timestamp) / (24 * 3600)
                if delta_days > 35:
                    self.log_result(self.ms_canceled_file, f"{full_line}")
                    print(f"{ColorPurple}{email} -> MS CANCELED?{ColorReset}")
                else:
                    self.log_result(self.ongoing_file, f"{full_line}")
                    self.log_result(self.ongoing_root_file, f"{full_line}")
                    print(f"{ColorYellow}{email} -> ONGOING{ColorReset}")
            else:
                self.log_result(self.error_file, f"{full_line} | Reason: No specific status found")
                print(f"{ColorGray}{email} -> OTHER ERROR{ColorReset}")

        except Exception as e:
            self.log_result(self.error_file, f"{full_line} | Reason: {str(e)}")
            print(f"{ColorGray}{email} -> EXCEPTION{ColorReset}")

    def run(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        selected_file = self.select_file()
        if not selected_file:
            return

        count, format_type = self.extract_emails(selected_file)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        format_tag = ""
        if format_type == "SV2":
            format_tag = " (SV2 format detected)"
        elif format_type == "UKN":
            format_tag = " (UKN format detected)"

        print(f"{ColorCyan}{ColorBold}NL CHECKER (NotLetters) - BY Chuborn{ColorReset}")
        print(f"{ColorGray}ltc1qnt9an3zncufvs2vcueuy5nh8q04s9l2q78svu7{ColorReset}\n")
        print(f"found {count} accounts in {selected_file}{format_tag}\n")
        
        if count == 0:
            return

        self.setup_results()

        with ThreadPoolExecutor(max_workers=10) as executor:
            for full_line, email, password in self.found_accounts:
                executor.submit(self.check_account, full_line, email, password)

if __name__ == "__main__":
    checker = NL_Checker()
    checker.run()
