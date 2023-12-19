import re

def extract_gmail_emails(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@gmail\.com\b', content)
        unique_emails = list(set(emails))  # Remove duplicates
        return unique_emails

def save_emails(emails, output_file):
    with open(output_file, 'a') as file:
        for email in emails:
            file.write(email + '\n')

# Usage example
input_file_path = 'clean_emails.txt'
output_file_path = 'gmail_emails.txt'

found_emails = extract_gmail_emails(input_file_path)
save_emails(found_emails, output_file_path)

print(f"Found and saved {len(found_emails)} Gmail email(s) to '{output_file_path}'.")
