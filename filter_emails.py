from dotenv import load_dotenv
import os

load_dotenv()
root = os.getenv("root")
clean_emails_file = root + os.getenv("emails_file")
valid_emails_file = root + os.getenv("valid_emails_file")

# Read the email addresses from the files
with open(valid_emails_file, "r") as valid_file:
    valid_emails = valid_file.read().splitlines()

with open(clean_emails_file, "r") as clean_file:
    clean_emails = clean_file.read().splitlines()

# Remove emails from the clean_emails list if they exist in valid_emails
clean_emails = [email for email in clean_emails if email.split(":")[1] not in valid_emails]

# Save the updated clean_emails list back to the file
with open(clean_emails_file, "w") as clean_file:
    clean_file.write("\n".join(clean_emails))
