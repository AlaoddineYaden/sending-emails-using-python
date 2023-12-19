import re

# Specify input and output file names
input_file = 'clean_emails.txt'
output_file = 'emails.txt'

# Define regular expression pattern to match email:password format
pattern = re.compile(r'(.+):(.+)')

# Create a set to store unique email addresses
unique_emails = set()

# Open input and output files
with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
    # Loop through lines in the input file
    for line in infile:
        # Use regular expression to extract email address
        match = pattern.match(line)
        if match:
            email = match.group(1)
            # Check if the email is not already in the set
            if email not in unique_emails:
                # Write the unique email address to the output file
                outfile.write(email + '\n')
                # Add the email to the set to keep track of uniqueness
                unique_emails.add(email)
