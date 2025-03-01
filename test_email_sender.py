import os
import unittest
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import sys
from io import StringIO
from email_sender import EmailSender
import socks

# Import the EmailSender class
# Assuming the main code is in a file called email_sender.py
sys.path.append('.')
try:
    from email_sender import EmailSender, SMTP_CONFIG, EMAIL_FILES
except ImportError:
    # If running the tests directly, define a mock class structure
    class EmailSender:
        pass
    SMTP_CONFIG = {
        "server": "smtp.gmail.com",
        "port": 587,
        "accounts": [
            {
                "username": "test@example.com",
                "password": "password123",
                "max_sending": 8,
            }
        ]
    }
    EMAIL_FILES = {
        "source": "./res/emails/my.txt",
        "valid": "./res/emails/valid_emails.txt",
        "template": "./res/templates/email_template_fr.html",
    }


class TestEmailSender(unittest.TestCase):
    """Test cases for the EmailSender class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary files for testing
        self.temp_files = {}
        for key in ['source', 'valid', 'template']:
            fd, path = tempfile.mkstemp()
            os.close(fd)
            self.temp_files[key] = path
            
        # Patch EMAIL_FILES dictionary
        self.email_files_patch = patch.dict(EMAIL_FILES, {
            "source": self.temp_files['source'],
            "valid": self.temp_files['valid'],
            "template": self.temp_files['template'],
        })
        self.email_files_patch.start()
        
        # Sample data
        self.sample_emails = ["1:test1@example.com", "2:test2@example.com"]
        self.sample_proxies = ["127.0.0.1:8080", "127.0.0.1:8081"]
        self.sample_template = "<html><body>Hello {email}</body></html>"
        
        # Write sample data to files
        with open(self.temp_files['source'], 'w') as f:
            f.write('\n'.join(self.sample_emails))
        with open(self.temp_files['template'], 'w') as f:
            f.write(self.sample_template)
            
        # Create EmailSender instance with mocked dependencies
        with patch('email_sender.EmailSender._load_file_lines') as mock_load_lines, \
             patch('email_sender.EmailSender._load_file_content') as mock_load_content:
            mock_load_lines.side_effect = [self.sample_emails, self.sample_proxies]
            mock_load_content.return_value = self.sample_template
            self.email_sender = EmailSender()
            
        # Reset counters
        self.email_sender.email_counter = 0
        self.email_sender.email_sent_in_session = 0
        self.email_sender.failed_email_counter = 1
        self.email_sender.account_index = 0

    def tearDown(self):
        """Tear down test fixtures."""
        # Remove temporary files
        for path in self.temp_files.values():
            try:
                os.remove(path)
            except OSError:
                pass
                
        # Stop patches
        self.email_files_patch.stop()

    def test_init(self):
        """Test initialization of EmailSender."""
        self.assertEqual(self.email_sender.email_list, self.sample_emails)
        self.assertEqual(self.email_sender.proxies, self.sample_proxies)
        self.assertEqual(self.email_sender.email_template, self.sample_template)
        self.assertEqual(self.email_sender.valid_emails, [])
        self.assertEqual(self.email_sender.email_counter, 0)
        self.assertEqual(self.email_sender.email_sent_in_session, 0)
        self.assertEqual(self.email_sender.failed_email_counter, 1)
        self.assertEqual(self.email_sender.account_index, 0)
        self.assertFalse(self.email_sender.stop_event.is_set())

    def test_load_file_lines(self):
        """Test loading lines from a file."""
        # Test with existing file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
            temp.write("line1\nline2\n")
            temp_name = temp.name
            
        lines = EmailSender._load_file_lines(temp_name)
        self.assertEqual(lines, ["line1", "line2"])
        os.unlink(temp_name)
        
        # Test with non-existent file
        non_existent = "/path/to/non/existent/file.txt"
        with patch('builtins.open', mock_open()) as m:
            lines = EmailSender._load_file_lines(non_existent)
            self.assertEqual(lines, [])
            m.assert_called_once_with(non_existent, "w")

    def test_load_file_content(self):
        """Test loading content from a file."""
        # Test with existing file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
            temp.write("file content")
            temp_name = temp.name
            
        content = EmailSender._load_file_content(temp_name)
        self.assertEqual(content, "file content")
        os.unlink(temp_name)
        
        # Test with non-existent file
        with patch('builtins.print') as mock_print:
            content = EmailSender._load_file_content("/path/to/non/existent/file.txt")
            self.assertEqual(content, "")
            mock_print.assert_called_once()

    @patch('smtplib.SMTP')
    @patch('socks.set_default_proxy')
    @patch('socks.socksocket')
    def test_smtp_connection(self, mock_socksocket, mock_set_proxy, mock_smtp):
        """Test SMTP connection context manager."""
        # Setup mocks
        mock_connection = MagicMock()
        mock_smtp.return_value = mock_connection
        
        # Original socket to be restored
        original_socket = socks.socket
        
        # Use the context manager
        with self.email_sender.smtp_connection("127.0.0.1:8080", "user", "pass"):
            # Verify proxy setup
            mock_set_proxy.assert_called_once_with(socks.HTTP, "127.0.0.1", 8080)
            # Verify SMTP connection
            mock_smtp.assert_called_once_with(SMTP_CONFIG["server"], SMTP_CONFIG["port"], timeout=30)
            # Verify TLS and login
            mock_connection.starttls.assert_called_once()
            mock_connection.login.assert_called_once_with("user", "pass")
            
        # Verify connection closed
        mock_connection.quit.assert_called_once()
        # Verify socket restored
        self.assertEqual(socks.socket, original_socket)

    @patch.object(EmailSender, 'smtp_connection')
    @patch.object(EmailSender, '_create_email_message')
    @patch.object(EmailSender, '_handle_successful_email')
    def test_send_email_success(self, mock_handle_success, mock_create_msg, mock_smtp_conn):
        """Test successful email sending."""
        # Setup mocks
        mock_smtp = MagicMock()
        mock_smtp_conn.return_value.__enter__.return_value = mock_smtp
        mock_msg = MagicMock()
        mock_create_msg.return_value = mock_msg
        
        # Call the method
        result = self.email_sender.send_email("1:test@example.com", "127.0.0.1:8080")
        
        # Verify the result
        self.assertEqual(result, "test@example.com")
        
        # Verify method calls
        mock_create_msg.assert_called_once_with(1, "test@example.com", SMTP_CONFIG["accounts"][0]["username"])
        mock_smtp.send_message.assert_called_once_with(mock_msg)
        mock_handle_success.assert_called_once_with("1:test@example.com", "test@example.com")

    @patch.object(EmailSender, 'smtp_connection')
    def test_send_email_failure(self, mock_smtp_conn):
        """Test email sending failure."""
        # Setup mock to raise an exception
        mock_smtp_conn.return_value.__enter__.side_effect = Exception("Connection error")
        
        # Call the method and verify the result
        result = self.email_sender.send_email("1:test@example.com", "127.0.0.1:8080")
        self.assertIsNone(result)
        
        # Verify failed counter incremented
        self.assertEqual(self.email_sender.failed_email_counter, 2)

    def test_create_email_message(self):
        """Test email message creation."""
        # Mock file attachment
        with patch('builtins.open', mock_open(read_data=b'file content')), \
             patch('email.encoders.encode_base64'):
            
            # Call the method
            msg = self.email_sender._create_email_message(1, "test@example.com", "sender@example.com")
            
            # Verify the message
            self.assertEqual(msg["Subject"], os.getenv("EMAIL_SUBJECT", "Application"))
            self.assertEqual(msg["From"], "sender@example.com")
            self.assertEqual(msg["To"], "test@example.com")
            
            # Check payload parts (simplified)
            payloads = msg.get_payload()
            self.assertEqual(len(payloads), 2)  # Attachment and HTML body

    def test_handle_successful_email(self):
        """Test handling after successful email sending."""
        # Add the email to the list
        email_data = "1:test@example.com"
        self.email_sender.email_list = [email_data]
        
        # Mock the file update method
        with patch.object(self.email_sender, '_update_source_email_file') as mock_update, \
             patch('builtins.open', mock_open()) as mock_file:
            
            # Call the method
            self.email_sender._handle_successful_email(email_data, "test@example.com")
            
            # Verify email removed from list
            self.assertNotIn(email_data, self.email_sender.email_list)
            
            # Verify file was updated
            mock_update.assert_called_once_with(email_data)
            
            # Verify valid email added to list and file
            self.assertIn("test@example.com", self.email_sender.valid_emails)
            mock_file.assert_called_once_with(EMAIL_FILES["valid"], "a")
            mock_file().write.assert_called_once_with("test@example.com\n")

    def test_update_source_email_file(self):
        """Test updating the source email file."""
        # Create a temp file with test content
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
            temp.write("1:keep@example.com\n2:remove@example.com\n3:keep2@example.com")
            temp_name = temp.name
            
        # Patch the source file path
        with patch.dict(EMAIL_FILES, {"source": temp_name}):
            # Call the method
            EmailSender()._update_source_email_file("2:remove@example.com")
            
            # Verify file content
            with open(temp_name, 'r') as f:
                content = f.read()
                self.assertIn("1:keep@example.com", content)
                self.assertIn("3:keep2@example.com", content)
                self.assertNotIn("2:remove@example.com", content)
                
        # Clean up
        os.unlink(temp_name)

    def test_should_change_account(self):
        """Test account change decision logic."""
        # Test max sending reached
        self.email_sender.email_sent_in_session = SMTP_CONFIG["accounts"][0]["max_sending"]
        self.assertTrue(self.email_sender.should_change_account())
        
        # Test failed counter threshold reached
        self.email_sender.email_sent_in_session = 0
        self.email_sender.failed_email_counter = 15  # Assuming failed_email_counter_limit is 15
        self.assertTrue(self.email_sender.should_change_account())
        
        # Test neither condition met
        self.email_sender.email_sent_in_session = 1
        self.email_sender.failed_email_counter = 1
        self.assertFalse(self.email_sender.should_change_account())

    def test_should_stop(self):
        """Test stop decision logic."""
        # Setup with last account
        self.email_sender.account_index = len(SMTP_CONFIG["accounts"]) - 1
        
        # Test max sending reached on last account
        self.email_sender.email_sent_in_session = SMTP_CONFIG["accounts"][-1]["max_sending"]
        self.assertTrue(self.email_sender.should_stop())
        
        # Verify counters reset
        self.assertEqual(self.email_sender.email_sent_in_session, 0)
        self.assertEqual(self.email_sender.account_index, 0)
        self.assertEqual(self.email_sender.failed_email_counter, 1)
        
        # Test not last account
        self.email_sender.account_index = 0
        self.email_sender.email_sent_in_session = SMTP_CONFIG["accounts"][0]["max_sending"]
        self.assertFalse(self.email_sender.should_stop())

    @patch.object(EmailSender, 'send_email')
    @patch('time.sleep')
    def test_run(self, mock_sleep, mock_send_email):
        """Test the main run method."""
        # Setup return values
        mock_send_email.side_effect = ["test1@example.com", None]
        
        # Setup data
        self.email_sender.email_list = ["1:test1@example.com", "2:test2@example.com"]
        self.email_sender.proxies = ["127.0.0.1:8080"]
        
        # Run with limited concurrency
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            # Setup mock executor
            mock_exec_instance = MagicMock()
            mock_executor.return_value.__enter__.return_value = mock_exec_instance
            
            # Execute run method
            self.email_sender.run()
            
            # Verify executor called with correct max_workers
            mock_executor.assert_called_once()
            
            # Verify submit called for each email
            self.assertEqual(mock_exec_instance.submit.call_count, 2)


# Integration test that mocks actual sending but verifies the full workflow
class TestEmailSenderIntegration(unittest.TestCase):
    """Integration tests for EmailSender."""
    
    @patch('smtplib.SMTP')
    @patch('socks.set_default_proxy')
    def test_end_to_end_workflow(self, mock_set_proxy, mock_smtp):
        """Test end-to-end workflow without actually sending emails."""
        # Create temporary files with test data
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            emails_path = os.path.join(temp_dir, "emails.txt")
            valid_path = os.path.join(temp_dir, "valid.txt")
            template_path = os.path.join(temp_dir, "template.html")
            proxy_path = os.path.join(temp_dir, "proxies.txt")
            
            # Write test data
            with open(emails_path, 'w') as f:
                f.write("1:test1@example.com\n2:test2@example.com\n")
            with open(template_path, 'w') as f:
                f.write("<html><body>Test template for {email}</body></html>")
            with open(proxy_path, 'w') as f:
                f.write("127.0.0.1:8080\n")
            open(valid_path, 'w').close()  # Create empty file
            
            # Patch file paths and SMTP config
            with patch.dict(EMAIL_FILES, {
                "source": emails_path,
                "valid": valid_path,
                "template": template_path,
            }), patch.dict(SMTP_CONFIG, {
                "accounts": [{
                    "username": "test@example.com",
                    "password": "password123",
                    "max_sending": 10,
                }]
            }), patch('email_sender.PROXY_FILES', {
                "working": proxy_path,
            }):
                
                # Setup mock SMTP
                mock_connection = MagicMock()
                mock_smtp.return_value = mock_connection
                
                # Capture stdout for verification
                captured_output = StringIO()
                sys.stdout = captured_output
                
                # Create sender and run
                sender = EmailSender()
                sender.proxies = ["127.0.0.1:8080"]  # Set directly to bypass loading
                
                # Run with patched executor to control execution
                with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
                    # Make the executor actually execute the function
                    def side_effect(fn, *args, **kwargs):
                        future = MagicMock()
                        result = fn(*args, **kwargs)
                        future.result.return_value = result
                        return future
                    
                    mock_exec = MagicMock()
                    mock_exec.submit.side_effect = side_effect
                    mock_executor.return_value.__enter__.return_value = mock_exec
                    
                    # Run the sender
                    sender.run()
                
                # Restore stdout
                sys.stdout = sys.__stdout__
                
                # Verify emails were processed
                output = captured_output.getvalue()
                self.assertIn("Successfully sent email", output)
                
                # Verify valid emails file was updated
                with open(valid_path, 'r') as f:
                    valid_content = f.read()
                    self.assertIn("test1@example.com", valid_content)
                    self.assertIn("test2@example.com", valid_content)
                
                # Verify source emails file was updated (should be empty)
                with open(emails_path, 'r') as f:
                    source_content = f.read()
                    self.assertEqual(source_content.strip(), "")


# Run the tests
if __name__ == "__main__":
    unittest.main()