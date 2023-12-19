import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from socket import socket
import threading
import time
import sys
import requests
from socket import socket
import socks
import random
from dotenv import load_dotenv
import os

load_dotenv()


root = os.getenv("root")
emails_file = root + os.getenv("emails_file")
valid_emails_file = root + os.getenv("valid_emails_file")
proxies_file = root + os.getenv("proxies_file")
working_proxies_file = root + os.getenv("working_proxies_file")
template_file = root + os.getenv("template_file")
email_subject = os.getenv("email_subject")

# Define the SMTP server and login credentials

smtp_server = "smtp.gmail.com"
smtp_port = 587


smtp_accounts = [
    # {
    #     "username": "brushheurt@gmail.com",
    #     "password": "jewcpignaibjafnn",
    #     "max_sending": 4000,
    # },
    {
        "username": "falahokama@gmail.com",
        "password": "tllofflvomcyyyxc",
        "max_sending": 400,
    },
    {
        "username": "cuddyduffy@gmail.com",
        "password": "wzqsjtgzhrnzsdnw",
        "max_sending": 800,
    },
    {
        "username": "tywannew@gmail.com",
        "password": "oyuxkqxtwafrpjdo",
        "max_sending": 800,
    },
]


# Read the list of email addresses from a file
# with open("clean_emails1.txt", "r") as f:
with open(emails_file, "r") as f:
    email_list = f.read().splitlines()

# Read the HTML template from a file
with open(template_file, "r") as f:
    email_template = f.read()

# Read the list of proxies from a file
with open(working_proxies_file, "r") as f:
    proxies = f.read().splitlines()

# Create a list to store the valid email addresses
valid_emails = []

# Counter to keep track of emails sent
email_counter = 0
counter = 0
failed_email_counter = 1  # Counter for failed emails
account_index = 0  # Initialize account_index with 1
##########
failed_email_counter_limit = 20
change_proxy_limit = 30
take_rest_after_email_counter = 100
max_workers = 30
##########
stop_event = threading.Event()


@contextmanager
def smtp_connection(proxy, username, password):
    socks.set_default_proxy(socks.HTTP, proxy.split(":")[0], int(proxy.split(":")[1]))
    socket.socket = socks.socksocket
    connection = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
    connection.starttls()
    connection.login(username, password)
    try:
        yield connection
    finally:
        connection.quit()


def send_email(email_data, proxy):
    global email_counter, failed_email_counter, account_index, stop_event

    try:
        email_id, email = email_data.split(":")
        email_id = int(email_id)

        account = smtp_accounts[account_index]
        smtp_username = account["username"]
        smtp_password = account["password"]

        # Create the email message
        msg = MIMEMultipart()
        msg["Subject"] = email_subject
        # msg["From"] = smtp_username
        msg["From"] = f"""Best Offers"""
        msg["To"] = email

        
        unsabscribe_line = f""" <p
                            style="font-family:helvetica;font-size:11px;font-weight:100;color:#000000;text-align:center;padding-bottom:24px">
                            Vous recevez cet e-mail car vous &ecirc;tes abonn&eacute; &agrave; notre newsletter. Si vous
                            ne souhaitez plus recevoir nos communications, <a
                                href="https://cuddy.pythonanywhere.com/unsubscribe/{email_id}"
                                style="color: #2596be; text-decoration: underline">cliquez ici pour vous
                                d&eacute;sinscrire</a>.
                        </p>
                    </td>
                </tr>

            </tbody>
        </table>
    </div>
</body>

</html>"""
       
       
#         unsabscribe_line = f""" <table><tr><td align="center" valign="top" style="padding: 40px"><p style="color: #666666; font-size: 13px; margin: 0">Vous recevez cet e-mail car vous &ecirc;tes abonn&eacute; &agrave; notre newsletter. Si vous ne souhaitez plus recevoir nos communications, <a href="https://cuddy.pythonanywhere.com/unsubscribe/{email_id}" style="color: #2596be; text-decoration: underline">cliquez ici pour vous
#  d&eacute;sinscrire</a>.</p></td></tr></table></div></body></html>"""
       
       
        image_line = f'<img src="https://cuddy.pythonanywhere.com/image/{email_id}" alt="img" alt="Logo" style="display: none; margin: 0 auto"/>'
        email_template1 = email_template + unsabscribe_line + image_line

        # Add HTML content to the message body
        html = email_template1.replace("{email}", email)
        body = MIMEText(html, "html")
        msg.attach(body)

        # Send the email
        with smtp_connection(proxy, smtp_username, smtp_password) as smtp:
            smtp.send_message(msg)

        email_list.remove(email_data)

        # Open the file in 'r+' mode to read and write
        with open(emails_file, 'r+') as f:
            content = f.readlines()
            f.seek(0)  # Move the file pointer to the beginning
            f.truncate()  # Truncate the file to remove its content

            # Write the updated email list back to the file
            for line in content:
                if line.strip() != email_data:
                    f.write(line)
                # Close the file again
        f.close()
        print(f"Successfully sent email to {email} using proxy {proxy}")
        valid_emails.append(email)
        with open(valid_emails_file, "a") as f:
            f.write(email + "\n")
        return email

    except Exception as e:
        # print(f"Failed to send email to {email} using proxy {proxy}: {str(e)}")
        failed_email_counter += 1
        print(
            f"user : {smtp_username} ---- {smtp_password} ---- {account_index}-------{failed_email_counter}---{e}"
        )
        return None


def should_stop():
    global failed_email_counter, account_index, counter
    if account_index == len(smtp_accounts) - 1:
        # print("inside 1 if "+str(account_index == len(smtp_accounts) - 1 ))
        if int(smtp_accounts[account_index]["max_sending"]) == counter:
            counter = 0
            account_index = 0
            failed_email_counter = 1
            return True

    return False


with ThreadPoolExecutor(max_workers=max_workers) as executor:
    proxy_index = 0
    for email_data in email_list:
        proxy = proxies[proxy_index]
        time.sleep(random.randint(1, 5))
        future = executor.submit(send_email, email_data, proxy)
        email_counter += 1
        counter += 1
        print(counter)
        if email_counter % change_proxy_limit == 0:
            proxy_index = (proxy_index + 1) % len(proxies)
            # print(f"Switching to next proxy: {proxy}")
        if email_counter % take_rest_after_email_counter == 0:
            print("waiting")
            time.sleep(random.randint(60, 240))

        if should_stop():
            print("Terminating due to too many failed emails...")
            print("Stopping threads...")
            stop_event.set()
            executor.shutdown(wait=False)
            break  # Exit the loop

        if failed_email_counter % failed_email_counter_limit == 0 and account_index == len(smtp_accounts) - 1:
            print("Terminating due to too many failed emails...")
            print("Stopping threads...")
            stop_event.set()
            executor.shutdown(wait=False)
            break  # Exit the loop

        if (
            smtp_accounts[account_index]["max_sending"] == counter
            or failed_email_counter % failed_email_counter_limit == 0
        ):
            print(f"---------------count reach limit {counter}-------------- ")
            counter = 0
            account_index = (account_index + 1) % len(smtp_accounts)
            failed_email_counter = 1

    executor.shutdown(wait=True)


# valid_emails_file = os.getenv("valid_emails_file")

# # Remove emails from the clean_emails list if they exist in valid_emails
# clean_emails = [
#     email for email in email_list if email.split(":")[1] not in valid_emails
# ]

# # Save the updated clean_emails list back to the file
# with open(emails_file, "w") as clean_file:
#     clean_file.write("\n".join(clean_emails))

print("Valid email addresses saved to file: valid_emails.txt")
