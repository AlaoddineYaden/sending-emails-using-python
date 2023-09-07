import re

def extract_gmail_emails(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@gmail\.com\b', content)
            unique_emails = list(set(emails))  # Remove duplicates
            return unique_emails
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return []

def save_emails(emails, output_file):
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            for email in emails:
                file.write(email + '\n')
        print(f"Found and saved {len(emails)} Gmail email(s) to '{output_file}'.")
    except IOError:
        print(f"Error: Unable to write to '{output_file}'.")

# Usage example
input_file_path = 'cc.txt'
output_file_path = 'gmail_emails.txt'

found_emails = extract_gmail_emails(input_file_path)
if found_emails:
    save_emails(found_emails, output_file_path)
