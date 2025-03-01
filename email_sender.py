import smtplib
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Tuple

import socks
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment variables



BASE_DIR = os.getenv("ROOT", ".")
EMAIL_FILES = {
    "source": os.path.join(BASE_DIR, os.getenv("EMAILS_FILE", "emails.txt")),
    "valid": os.path.join(BASE_DIR, os.getenv("VALID_EMAILS_FILE", "valid_emails.txt")),
    "template": os.path.join(BASE_DIR, os.getenv("TEMPLATE_FILE", "template.html")),
}
PROXY_FILES = {
    "all": os.path.join(BASE_DIR, os.getenv("PROXIES_FILE", "proxies.txt")),
    "working": os.path.join(BASE_DIR, os.getenv("WORKING_PROXIES_FILE", "working_proxies.txt")),
}
CV_PATH = os.path.join(BASE_DIR, os.getenv("CV_PATH", "cv.pdf"))
EMAIL_SUBJECT = os.getenv("EMAIL_SUBJECT", "Application")



# SMTP Configuration
SMTP_CONFIG = {
    "server": "smtp.gmail.com",
    "port": 587,
    "accounts": [
        {
            "username": os.getenv("SMTP_USERNAME_1"),
            "password": os.getenv("SMTP_PASSWORD_1"),
            "max_sending": int(os.getenv("SMTP_MAX_SENDING_1", "8")),
        },
        # Add more accounts as needed from environment variables
    ]
}

# Email sending limits and configurations
EMAIL_LIMITS = {
    "failed_email_counter_limit": int(os.getenv("FAILED_EMAIL_COUNTER_LIMIT", "15")),
    "change_proxy_limit": int(os.getenv("CHANGE_PROXY_LIMIT", "30")),
    "take_rest_after_email_counter": int(os.getenv("TAKE_REST_AFTER_EMAIL_COUNTER", "100")),
    "max_workers": int(os.getenv("MAX_WORKERS", "40")),
}

testing_mode = None


def get_testing_mode():
    """Check if application is running in testing mode."""
    return os.getenv('EMAIL_SENDER_TESTING_MODE', 'false').lower() == 'true'


class EmailSender:
    def __init__(self):
        self.testing_mode = testing_mode if testing_mode is not None else get_testing_mode() # type: ignore

        self.email_list = self._load_file_lines(EMAIL_FILES["source"])
        self.proxies = self._load_file_lines(PROXY_FILES["working"])
        self.email_template = self._load_file_content(EMAIL_FILES["template"])
        self.valid_emails = []
        
        # Counters and state tracking
        self.email_counter = 0
        self.email_sent_in_session = 0
        self.failed_email_counter = 1
        self.account_index = 0
        
        # Threading control
        self.stop_event = threading.Event()

    @staticmethod
    def _load_file_lines(filepath: str) -> List[str]:
        """Load lines from a file into a list."""
        try:
            with open(filepath, "r") as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"Warning: File {filepath} not found. Creating empty file.")
            with open(filepath, "w") as f:
                pass
            return []

    @staticmethod
    def _load_file_content(filepath: str) -> str:
        """Load entire file content as a string."""
        try:
            with open(filepath, "r") as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: Template file {filepath} not found.")
            return ""

    @contextmanager
    def smtp_connection(self, proxy: str, username: str, password: str):
        """Context manager for SMTP connections through a proxy."""
        # Store original socket for restoration
        original_socket = socks.socket
        
        try:
            # Set up proxy
            proxy_host, proxy_port = proxy.split(":")
            socks.set_default_proxy(socks.HTTP, proxy_host, int(proxy_port))
            socks.socket = socks.socksocket
            
            # Establish connection
            connection = smtplib.SMTP(SMTP_CONFIG["server"], SMTP_CONFIG["port"], timeout=30)
            connection.starttls()
            connection.login(username, password)
            yield connection
        finally:
            # Restore original socket and close connection
            socks.socket = original_socket
            if 'connection' in locals():
                connection.quit()

    def send_email(self, email_data: str, proxy: str) -> Optional[str]:
        """Send an email to a specific recipient using a proxy."""
        try:
            email_id, email = email_data.split(":")
            email_id = int(email_id)

            # Get current account details
            account = SMTP_CONFIG["accounts"][self.account_index]
            smtp_username = account["username"]
            smtp_password = account["password"]

            # Create email message
            msg = self._create_email_message(email_id, email, smtp_username)

            # In testing mode, don't actually send the email
            if self.testing_mode:
                print(f"[TESTING MODE] Would send email to {email} using proxy {proxy}")
                # Simulate successful sending
                self._handle_successful_email(email_data, email)
                return email

            # Send the email (only in non-testing mode)
            with self.smtp_connection(proxy, smtp_username, smtp_password) as smtp:
                smtp.send_message(msg)

            # Update tracking files
            self._handle_successful_email(email_data, email)
            
            print(f"Successfully sent email to {email} using proxy {proxy}")
            return email

        except Exception as e:
            self.failed_email_counter += 1
            print(f"Error sending to {email_data}: {str(e)}")
            print(f"Account: {smtp_username} | Account index: {self.account_index} | Failures: {self.failed_email_counter}")
            return None
    
    def _create_email_message(self, email_id: int, recipient_email: str, sender_email: str) -> MIMEMultipart:
        """Create the email message with attachments and tracking pixels."""
        msg = MIMEMultipart()
        msg["Subject"] = EMAIL_SUBJECT
        msg["From"] = sender_email
        msg["To"] = recipient_email

        # Attach CV PDF
        self._attach_file(msg, CV_PATH)

        # Add tracking pixel
        image_line = f'<img src="https://cuddy.pythonanywhere.com/image/{email_id}" alt="img" style="display: none; margin: 0 auto"/>'
        
        # Add HTML content
        html_content = self.email_template + image_line
        html_content = html_content.replace("{email}", recipient_email)
        body = MIMEText(html_content, "html")
        msg.attach(body)

        return msg

    @staticmethod
    def _attach_file(msg: MIMEMultipart, file_path: str) -> None:
        """Attach a file to the email message."""
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(file_path)}",
            )
            msg.attach(part)
        except FileNotFoundError:
            print(f"Warning: Attachment file {file_path} not found")

    def _handle_successful_email(self, email_data: str, email: str) -> None:
        """Update files and lists after successfully sending an email."""
        # Remove from email list
        if email_data in self.email_list:
            self.email_list.remove(email_data)

        # Update the source email file
        self._update_source_email_file(email_data)

        # Add to valid emails
        self.valid_emails.append(email)
        with open(EMAIL_FILES["valid"], "a") as f:
            f.write(email + "\n")

    def _update_source_email_file(self, email_data_to_remove: str) -> None:
        """Remove an email from the source file."""
        try:
            with open(EMAIL_FILES["source"], 'r') as f:
                lines = f.readlines()
            
            with open(EMAIL_FILES["source"], 'w') as f:
                for line in lines:
                    if line.strip() != email_data_to_remove:
                        f.write(line)
        except Exception as e:
            print(f"Error updating source email file: {str(e)}")

    def should_change_account(self) -> bool:
        """Check if we need to switch to the next account."""
        current_account = SMTP_CONFIG["accounts"][self.account_index]
        return (self.email_sent_in_session >= current_account["max_sending"] or 
                self.failed_email_counter % EMAIL_LIMITS["failed_email_counter_limit"] == 0)

    def should_stop(self) -> bool:
        """Check if we need to stop the email sending process."""
        if self.account_index == len(SMTP_CONFIG["accounts"]) - 1:
            current_account = SMTP_CONFIG["accounts"][self.account_index]
            if self.email_sent_in_session >= current_account["max_sending"]:
                self.email_sent_in_session = 0
                self.account_index = 0
                self.failed_email_counter = 1
                return True
        return False

    def run(self) -> None:
        """Run the email sending process with multiple threads."""
        if not self.email_list or not self.proxies or not self.email_template:
            print("Error: Missing required data (emails, proxies, or template)")
            return

        with ThreadPoolExecutor(max_workers=EMAIL_LIMITS["max_workers"]) as executor:
            proxy_index = 0
            futures = []

            for email_data in self.email_list:
                # Check if we should stop
                if self.stop_event.is_set() or self.should_stop():
                    print("Stopping email sending process...")
                    break

                # Check if we should change account
                if self.should_change_account():
                    print(f"Switching accounts: sent {self.email_sent_in_session} emails with current account")
                    self.email_sent_in_session = 0
                    self.account_index = (self.account_index + 1) % len(SMTP_CONFIG["accounts"])
                    self.failed_email_counter = 1
                    
                    # Check if we've gone through all accounts
                    if self.account_index == 0:
                        print("Cycled through all accounts, taking a break...")
                        time.sleep(random.randint(60, 120))

                # Select proxy and submit email sending task
                proxy = self.proxies[proxy_index]
                future = executor.submit(self.send_email, email_data, proxy)
                futures.append(future)
                
                # Update counters
                self.email_counter += 1
                self.email_sent_in_session += 1
                
                # Throttling and proxy rotation
                time.sleep(random.randint(1, 5))
                
                if self.email_counter % EMAIL_LIMITS["change_proxy_limit"] == 0:
                    proxy_index = (proxy_index + 1) % len(self.proxies)
                    print(f"Switching to next proxy: {self.proxies[proxy_index]}")
                
                if self.email_counter % EMAIL_LIMITS["take_rest_after_email_counter"] == 0:
                    print("Taking a short break...")
                    time.sleep(random.randint(20, 40))
                
            # Wait for all tasks to complete or be cancelled
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"Task exception: {str(e)}")

        print("Email sending process completed")
        print(f"Successfully sent emails: {len(self.valid_emails)}")
        print(f"Failed email attempts: {self.failed_email_counter - 1}")


if __name__ == "__main__":
    # Check if SMTP credentials are set
    if not SMTP_CONFIG["accounts"][0]["username"] or not SMTP_CONFIG["accounts"][0]["password"]:
        print("Error: SMTP credentials not set in environment variables")
        exit(1)
        
    sender = EmailSender()
    sender.run()