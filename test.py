from validate_email import validate_email
from dotenv import load_dotenv
import os

load_dotenv()
# root = os.getenv("root")
# emails_file = root + os.getenv("emails_file")
# valid_emails_file = root + os.getenv("valid_emails_file")

def check_email_existence(email_to_check):
    is_valid = validate_email(email_to_check)
    return is_valid

# Define input and output file names
input_file = "gmail_emails.txt"
output_file = "valid_emails.txt"

# Read emails from the input file and validate/save the valid ones
valid_emails = []

try:
    with open(input_file, "r") as file:
        for line in file:
            email = line.strip()  # Remove leading/trailing whitespace
            result = check_email_existence(email)
            
            if result:
                valid_emails.append(email)
                print(f"The email '{email}' exists and is valid.")
            else:
                print(f"The email '{email}' does not exist or is invalid.")

    # Save the valid emails to the output file
    with open(output_file, "w") as valid_file:
        valid_file.write("\n".join(valid_emails))

    print(f"Valid emails saved to '{output_file}'.")

except FileNotFoundError:
    print(f"Input file '{input_file}' not found.")

except Exception as e:
    print(f"An error occurred: {e}")

