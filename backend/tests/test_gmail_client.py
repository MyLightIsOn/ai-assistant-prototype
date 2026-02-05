"""
Tests for Gmail client read functionality.

This module tests the Gmail API integration for reading emails,
listing messages, searching, and downloading attachments.
"""

import base64
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from googleapiclient.errors import HttpError


# Mock the gmail_client module before importing
@pytest.fixture
def mock_credentials():
    """Mock Google credentials."""
    mock_creds = Mock()
    mock_creds.valid = True
    mock_creds.expired = False
    return mock_creds


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service."""
    return MagicMock()


@pytest.fixture
def sample_email_metadata():
    """Sample email metadata from Gmail API."""
    return {
        'id': 'msg123',
        'threadId': 'thread456',
        'labelIds': ['INBOX', 'UNREAD'],
        'snippet': 'This is a test email snippet...',
        'internalDate': '1704067200000',  # 2024-01-01 00:00:00
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'To', 'value': 'recipient@example.com'},
                {'name': 'Subject', 'value': 'Test Subject'},
                {'name': 'Date', 'value': 'Mon, 01 Jan 2024 00:00:00 +0000'},
            ],
            'mimeType': 'text/plain',
            'body': {
                'size': 100,
                'data': base64.urlsafe_b64encode(b'Test email body').decode('utf-8'),
            }
        }
    }


@pytest.fixture
def sample_email_with_attachment():
    """Sample email with attachment."""
    return {
        'id': 'msg789',
        'threadId': 'thread789',
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'Subject', 'value': 'Email with attachment'},
            ],
            'mimeType': 'multipart/mixed',
            'parts': [
                {
                    'mimeType': 'text/plain',
                    'body': {
                        'data': base64.urlsafe_b64encode(b'Email body with attachment').decode('utf-8'),
                    }
                },
                {
                    'filename': 'document.pdf',
                    'mimeType': 'application/pdf',
                    'body': {
                        'attachmentId': 'attach123',
                        'size': 5000,
                    }
                }
            ]
        }
    }


@pytest.fixture
def sample_message_list():
    """Sample message list response."""
    return {
        'messages': [
            {'id': 'msg1', 'threadId': 'thread1'},
            {'id': 'msg2', 'threadId': 'thread2'},
            {'id': 'msg3', 'threadId': 'thread3'},
        ],
        'resultSizeEstimate': 3,
    }


class TestGmailClientReadEmail:
    """Test read_email function."""

    @patch('gmail_client.get_gmail_service')
    def test_read_email_success(self, mock_get_service, mock_gmail_service, sample_email_metadata):
        """Test successfully reading an email."""
        from gmail_client import read_email

        # Setup mock
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().get().execute.return_value = sample_email_metadata

        # Execute
        result = read_email('msg123')

        # Verify
        assert result is not None
        assert result['id'] == 'msg123'
        assert result['subject'] == 'Test Subject'
        assert result['from'] == 'sender@example.com'
        assert result['to'] == 'recipient@example.com'
        assert result['snippet'] == 'This is a test email snippet...'
        assert 'body' in result
        assert 'Test email body' in result['body']

        # Verify API call (check call_args instead of assert_called_once due to mock chaining)
        call_args = mock_gmail_service.users().messages().get.call_args
        assert call_args[1] == {'userId': 'me', 'id': 'msg123', 'format': 'full'}

    @patch('gmail_client.get_gmail_service')
    def test_read_email_not_found(self, mock_get_service, mock_gmail_service):
        """Test reading non-existent email."""
        from gmail_client import read_email

        # Setup mock to raise 404
        mock_get_service.return_value = mock_gmail_service
        mock_error = HttpError(
            resp=Mock(status=404),
            content=b'Not Found'
        )
        mock_gmail_service.users().messages().get().execute.side_effect = mock_error

        # Execute and verify exception
        with pytest.raises(ValueError, match="Email not found"):
            read_email('nonexistent')

    @patch('gmail_client.get_gmail_service')
    def test_read_email_with_html_body(self, mock_get_service, mock_gmail_service):
        """Test reading email with HTML body."""
        from gmail_client import read_email

        # Setup mock with HTML content
        html_email = {
            'id': 'msg456',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'HTML Email'},
                ],
                'mimeType': 'multipart/alternative',
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {
                            'data': base64.urlsafe_b64encode(b'Plain text').decode('utf-8'),
                        }
                    },
                    {
                        'mimeType': 'text/html',
                        'body': {
                            'data': base64.urlsafe_b64encode(b'<html><body>HTML content</body></html>').decode('utf-8'),
                        }
                    }
                ]
            }
        }
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().get().execute.return_value = html_email

        # Execute
        result = read_email('msg456')

        # Verify both plain and HTML bodies are included
        assert result is not None
        assert 'body' in result
        assert 'html_body' in result
        assert 'Plain text' in result['body']
        assert 'HTML content' in result['html_body']


class TestGmailClientListEmails:
    """Test list_emails function."""

    @patch('gmail_client.get_gmail_service')
    def test_list_emails_default(self, mock_get_service, mock_gmail_service, sample_message_list):
        """Test listing emails with default parameters."""
        from gmail_client import list_emails

        # Setup mock
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().list().execute.return_value = sample_message_list

        # Execute
        result = list_emails()

        # Verify
        assert result is not None
        assert len(result['messages']) == 3
        assert result['messages'][0]['id'] == 'msg1'

        # Verify API call (check call_args instead of assert_called_once due to mock chaining)
        call_args = mock_gmail_service.users().messages().list.call_args
        assert call_args[1] == {'userId': 'me', 'maxResults': 10, 'q': ''}

    @patch('gmail_client.get_gmail_service')
    def test_list_emails_with_query(self, mock_get_service, mock_gmail_service, sample_message_list):
        """Test listing emails with custom query."""
        from gmail_client import list_emails

        # Setup mock
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().list().execute.return_value = sample_message_list

        # Execute
        result = list_emails(query='is:unread', max_results=5)

        # Verify API call (check call_args instead of assert_called_once due to mock chaining)
        call_args = mock_gmail_service.users().messages().list.call_args
        assert call_args[1] == {'userId': 'me', 'maxResults': 5, 'q': 'is:unread'}

    @patch('gmail_client.get_gmail_service')
    def test_list_emails_pagination(self, mock_get_service, mock_gmail_service):
        """Test listing emails with pagination."""
        from gmail_client import list_emails

        # Setup mock with pagination
        first_page = {
            'messages': [{'id': 'msg1'}, {'id': 'msg2'}],
            'nextPageToken': 'token123',
        }
        second_page = {
            'messages': [{'id': 'msg3'}, {'id': 'msg4'}],
        }

        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().list().execute.side_effect = [first_page, second_page]

        # Execute
        result = list_emails(max_results=4, include_all_pages=True)

        # Verify we got all messages
        assert len(result['messages']) == 4
        assert result['messages'][0]['id'] == 'msg1'
        assert result['messages'][3]['id'] == 'msg4'

    @patch('gmail_client.get_gmail_service')
    def test_list_emails_empty_result(self, mock_get_service, mock_gmail_service):
        """Test listing emails with no results."""
        from gmail_client import list_emails

        # Setup mock with empty result
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().list().execute.return_value = {
            'resultSizeEstimate': 0,
        }

        # Execute
        result = list_emails(query='nonexistent')

        # Verify
        assert result is not None
        assert result.get('messages', []) == []


class TestGmailClientSearchEmails:
    """Test search_emails function."""

    @patch('gmail_client.get_gmail_service')
    def test_search_by_sender(self, mock_get_service, mock_gmail_service, sample_message_list):
        """Test searching emails by sender."""
        from gmail_client import search_emails

        # Setup mock
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().list().execute.return_value = sample_message_list

        # Execute
        result = search_emails(from_email='sender@example.com')

        # Verify query construction
        call_args = mock_gmail_service.users().messages().list.call_args
        assert 'from:sender@example.com' in call_args[1]['q']

    @patch('gmail_client.get_gmail_service')
    def test_search_by_subject(self, mock_get_service, mock_gmail_service, sample_message_list):
        """Test searching emails by subject."""
        from gmail_client import search_emails

        # Setup mock
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().list().execute.return_value = sample_message_list

        # Execute
        result = search_emails(subject='Test Subject')

        # Verify query construction
        call_args = mock_gmail_service.users().messages().list.call_args
        assert 'subject:Test Subject' in call_args[1]['q']

    @patch('gmail_client.get_gmail_service')
    def test_search_by_date(self, mock_get_service, mock_gmail_service, sample_message_list):
        """Test searching emails after a specific date."""
        from gmail_client import search_emails

        # Setup mock
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().list().execute.return_value = sample_message_list

        # Execute
        after_date = datetime(2024, 1, 1)
        result = search_emails(after_date=after_date)

        # Verify query construction
        call_args = mock_gmail_service.users().messages().list.call_args
        assert 'after:2024/01/01' in call_args[1]['q']

    @patch('gmail_client.get_gmail_service')
    def test_search_combined_criteria(self, mock_get_service, mock_gmail_service, sample_message_list):
        """Test searching with multiple criteria."""
        from gmail_client import search_emails

        # Setup mock
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().list().execute.return_value = sample_message_list

        # Execute
        result = search_emails(
            from_email='sender@example.com',
            subject='Invoice',
            after_date=datetime(2024, 1, 1),
            has_attachment=True
        )

        # Verify query construction
        call_args = mock_gmail_service.users().messages().list.call_args
        query = call_args[1]['q']
        assert 'from:sender@example.com' in query
        assert 'subject:Invoice' in query
        assert 'after:2024/01/01' in query
        assert 'has:attachment' in query


class TestGmailClientDownloadAttachment:
    """Test download_attachment function."""

    @patch('gmail_client.get_gmail_service')
    def test_download_attachment_success(self, mock_get_service, mock_gmail_service):
        """Test successfully downloading an attachment."""
        from gmail_client import download_attachment

        # Setup mock
        attachment_data = base64.urlsafe_b64encode(b'PDF file content').decode('utf-8')
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().attachments().get().execute.return_value = {
            'data': attachment_data,
            'size': 16,
        }

        # Execute
        result = download_attachment('msg123', 'attach456')

        # Verify
        assert result is not None
        assert result['data'] == b'PDF file content'
        assert result['size'] == 16

        # Verify API call (check call_args instead of assert_called_once due to mock chaining)
        call_args = mock_gmail_service.users().messages().attachments().get.call_args
        assert call_args[1] == {'userId': 'me', 'messageId': 'msg123', 'id': 'attach456'}

    @patch('gmail_client.get_gmail_service')
    def test_download_attachment_not_found(self, mock_get_service, mock_gmail_service):
        """Test downloading non-existent attachment."""
        from gmail_client import download_attachment

        # Setup mock to raise 404
        mock_get_service.return_value = mock_gmail_service
        mock_error = HttpError(
            resp=Mock(status=404),
            content=b'Not Found'
        )
        mock_gmail_service.users().messages().attachments().get().execute.side_effect = mock_error

        # Execute and verify exception
        with pytest.raises(ValueError, match="Attachment not found"):
            download_attachment('msg123', 'nonexistent')

    @patch('gmail_client.get_gmail_service')
    def test_save_attachment_to_file(self, mock_get_service, mock_gmail_service, tmp_path):
        """Test saving attachment to file."""
        from gmail_client import download_attachment

        # Setup mock
        attachment_data = base64.urlsafe_b64encode(b'PDF file content').decode('utf-8')
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().attachments().get().execute.return_value = {
            'data': attachment_data,
            'size': 16,
        }

        # Execute
        output_path = tmp_path / "test_attachment.pdf"
        result = download_attachment('msg123', 'attach456', save_path=str(output_path))

        # Verify file was created
        assert output_path.exists()
        assert output_path.read_bytes() == b'PDF file content'
        assert result['saved_to'] == str(output_path)


class TestGmailClientParsingUtilities:
    """Test email parsing utility functions."""

    def test_extract_text_from_plain(self):
        """Test extracting text from plain text email."""
        from gmail_client import extract_text_from_payload

        payload = {
            'mimeType': 'text/plain',
            'body': {
                'data': base64.urlsafe_b64encode(b'Plain text content').decode('utf-8'),
            }
        }

        result = extract_text_from_payload(payload)
        assert result == 'Plain text content'

    def test_extract_text_from_multipart(self):
        """Test extracting text from multipart email."""
        from gmail_client import extract_text_from_payload

        payload = {
            'mimeType': 'multipart/mixed',
            'parts': [
                {
                    'mimeType': 'text/plain',
                    'body': {
                        'data': base64.urlsafe_b64encode(b'First part').decode('utf-8'),
                    }
                },
                {
                    'mimeType': 'text/plain',
                    'body': {
                        'data': base64.urlsafe_b64encode(b'Second part').decode('utf-8'),
                    }
                }
            ]
        }

        result = extract_text_from_payload(payload)
        assert 'First part' in result
        assert 'Second part' in result

    def test_parse_headers(self):
        """Test parsing email headers."""
        from gmail_client import parse_headers

        headers = [
            {'name': 'From', 'value': 'sender@example.com'},
            {'name': 'To', 'value': 'recipient@example.com'},
            {'name': 'Subject', 'value': 'Test Email'},
            {'name': 'Date', 'value': 'Mon, 01 Jan 2024 00:00:00 +0000'},
            {'name': 'Message-ID', 'value': '<abc123@example.com>'},
        ]

        result = parse_headers(headers)
        assert result['from'] == 'sender@example.com'
        assert result['to'] == 'recipient@example.com'
        assert result['subject'] == 'Test Email'
        assert result['date'] == 'Mon, 01 Jan 2024 00:00:00 +0000'
        assert result['message_id'] == '<abc123@example.com>'

    def test_get_attachment_info(self, sample_email_with_attachment):
        """Test extracting attachment information."""
        from gmail_client import get_attachment_info

        result = get_attachment_info(sample_email_with_attachment)

        assert len(result) == 1
        assert result[0]['filename'] == 'document.pdf'
        assert result[0]['mime_type'] == 'application/pdf'
        assert result[0]['attachment_id'] == 'attach123'
        assert result[0]['size'] == 5000

    def test_get_attachment_info_no_attachments(self, sample_email_metadata):
        """Test extracting attachment info from email with no attachments."""
        from gmail_client import get_attachment_info

        result = get_attachment_info(sample_email_metadata)
        assert result == []


class TestGmailClientErrorHandling:
    """Test error handling in Gmail client."""

    @patch('gmail_client.get_gmail_service')
    def test_authentication_error(self, mock_get_service):
        """Test handling authentication errors."""
        from gmail_client import read_email

        # Setup mock to raise authentication error
        mock_error = HttpError(
            resp=Mock(status=401),
            content=b'Unauthorized'
        )
        mock_get_service.side_effect = mock_error

        # Execute and verify exception
        with pytest.raises(ValueError, match="Authentication failed"):
            read_email('msg123')

    @patch('gmail_client.get_gmail_service')
    def test_rate_limit_error(self, mock_get_service, mock_gmail_service):
        """Test handling rate limit errors."""
        from gmail_client import list_emails

        # Setup mock to raise rate limit error
        mock_get_service.return_value = mock_gmail_service
        mock_error = HttpError(
            resp=Mock(status=429),
            content=b'Rate Limit Exceeded'
        )
        mock_gmail_service.users().messages().list().execute.side_effect = mock_error

        # Execute and verify exception
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            list_emails()

    @patch('gmail_client.get_gmail_service')
    def test_network_error(self, mock_get_service, mock_gmail_service):
        """Test handling network errors."""
        from gmail_client import read_email

        # Setup mock to raise network error
        mock_get_service.return_value = mock_gmail_service
        mock_gmail_service.users().messages().get().execute.side_effect = ConnectionError("Network unavailable")

        # Execute and verify exception
        with pytest.raises(ConnectionError):
            read_email('msg123')


class TestGmailClientCredentials:
    """Test credential handling."""

    @patch('gmail_client.Credentials.from_authorized_user_file')
    @patch('os.path.exists')
    def test_get_gmail_service_with_existing_credentials(self, mock_exists, mock_from_file):
        """Test getting Gmail service with existing credentials."""
        from gmail_client import get_gmail_service

        # Setup mocks
        mock_exists.return_value = True
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_from_file.return_value = mock_creds

        # Execute
        service = get_gmail_service()

        # Verify
        assert service is not None
        mock_from_file.assert_called_once()

    @patch('os.path.exists')
    def test_get_gmail_service_without_credentials(self, mock_exists):
        """Test getting Gmail service without credentials."""
        from gmail_client import get_gmail_service

        # Setup mock
        mock_exists.return_value = False

        # Execute and verify exception
        with pytest.raises(FileNotFoundError, match="Credentials file not found"):
            get_gmail_service()
