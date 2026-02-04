"""
Tests for ntfy.sh notification client.

Following TDD: These tests are written FIRST before implementation.
All tests should FAIL initially until the implementation is complete.
"""

import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest
import requests

# Import will fail initially - this is expected in TDD
from ntfy_client import send_notification, NotificationConfig, NotificationError


class TestNotificationConfig:
    """Test configuration loading from environment variables."""

    def test_loads_config_from_environment(self):
        """Loads NTFY_URL, NTFY_USERNAME, and NTFY_PASSWORD from environment."""
        with patch.dict(os.environ, {
            'NTFY_URL': 'http://localhost:8080/test-topic',
            'NTFY_USERNAME': 'test-user',
            'NTFY_PASSWORD': 'test-password'
        }):
            config = NotificationConfig()

            assert config.url == 'http://localhost:8080/test-topic'
            assert config.username == 'test-user'
            assert config.password == 'test-password'

    def test_raises_error_when_url_missing(self):
        """Raises error if NTFY_URL environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="NTFY_URL"):
                NotificationConfig()

    def test_allows_missing_credentials(self):
        """Allows missing username/password for unauthenticated servers."""
        with patch.dict(os.environ, {
            'NTFY_URL': 'http://localhost:8080/public-topic'
        }, clear=True):
            config = NotificationConfig()

            assert config.url == 'http://localhost:8080/public-topic'
            assert config.username is None
            assert config.password is None


class TestSendNotification:
    """Test notification sending functionality."""

    @patch('ntfy_client.requests.post')
    def test_sends_notification_successfully(self, mock_post):
        """Sends notification with title and message to ntfy server."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'test123'}
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {
            'NTFY_URL': 'http://localhost:8080/notifications',
            'NTFY_USERNAME': 'user',
            'NTFY_PASSWORD': 'pass'
        }):
            result = send_notification(
                title='Test Title',
                message='Test message body'
            )

        assert result is True
        mock_post.assert_called_once()

    @patch('ntfy_client.requests.post')
    def test_includes_authentication_headers(self, mock_post):
        """Includes Basic Auth headers when credentials are configured."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {
            'NTFY_URL': 'http://localhost:8080/notifications',
            'NTFY_USERNAME': 'testuser',
            'NTFY_PASSWORD': 'testpass'
        }):
            send_notification(title='Test', message='Message')

        # Verify auth was passed to requests.post
        call_kwargs = mock_post.call_args.kwargs
        assert 'auth' in call_kwargs
        assert call_kwargs['auth'] == ('testuser', 'testpass')

    @patch('ntfy_client.requests.post')
    def test_formats_priority_correctly(self, mock_post):
        """Formats priority header according to ntfy spec (1-5 or named)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {'NTFY_URL': 'http://localhost:8080/test'}):
            send_notification(
                title='Test',
                message='Message',
                priority='high'
            )

        # Check that priority was included in headers
        call_kwargs = mock_post.call_args.kwargs
        assert 'headers' in call_kwargs
        assert 'X-Priority' in call_kwargs['headers']
        assert call_kwargs['headers']['X-Priority'] == 'high'

    @patch('ntfy_client.requests.post')
    def test_formats_tags_correctly(self, mock_post):
        """Formats tags as comma-separated list in headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {'NTFY_URL': 'http://localhost:8080/test'}):
            send_notification(
                title='Test',
                message='Message',
                tags='warning,ai,task-complete'
            )

        call_kwargs = mock_post.call_args.kwargs
        assert 'headers' in call_kwargs
        assert 'X-Tags' in call_kwargs['headers']
        assert call_kwargs['headers']['X-Tags'] == 'warning,ai,task-complete'

    @patch('ntfy_client.requests.post')
    def test_formats_title_in_headers(self, mock_post):
        """Sends title in X-Title header, message in body."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {'NTFY_URL': 'http://localhost:8080/test'}):
            send_notification(
                title='Important Alert',
                message='Something happened'
            )

        call_kwargs = mock_post.call_args.kwargs
        assert 'headers' in call_kwargs
        assert call_kwargs['headers']['X-Title'] == 'Important Alert'

        # Message should be in the data parameter
        assert call_kwargs.get('data') == 'Something happened'

    @patch('ntfy_client.requests.post')
    def test_handles_connection_error_gracefully(self, mock_post):
        """Returns False and logs error when connection fails."""
        mock_post.side_effect = requests.ConnectionError('Connection refused')

        with patch.dict(os.environ, {'NTFY_URL': 'http://localhost:8080/test'}):
            result = send_notification(title='Test', message='Message')

        assert result is False

    @patch('ntfy_client.requests.post')
    def test_handles_timeout_gracefully(self, mock_post):
        """Returns False when request times out."""
        mock_post.side_effect = requests.Timeout('Request timed out')

        with patch.dict(os.environ, {'NTFY_URL': 'http://localhost:8080/test'}):
            result = send_notification(title='Test', message='Message')

        assert result is False

    @patch('ntfy_client.requests.post')
    def test_handles_http_error_gracefully(self, mock_post):
        """Returns False when server returns error status."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError('Server error')
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {'NTFY_URL': 'http://localhost:8080/test'}):
            result = send_notification(title='Test', message='Message')

        assert result is False

    @patch('ntfy_client.requests.post')
    def test_uses_default_priority_when_not_specified(self, mock_post):
        """Uses 'default' priority when priority parameter is not provided."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {'NTFY_URL': 'http://localhost:8080/test'}):
            send_notification(title='Test', message='Message')

        call_kwargs = mock_post.call_args.kwargs
        # Should use default priority or not set priority header
        if 'headers' in call_kwargs and 'X-Priority' in call_kwargs['headers']:
            assert call_kwargs['headers']['X-Priority'] == 'default'

    @patch('ntfy_client.requests.post')
    def test_omits_tags_when_not_specified(self, mock_post):
        """Does not include X-Tags header when tags parameter is None."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {'NTFY_URL': 'http://localhost:8080/test'}):
            send_notification(title='Test', message='Message', tags=None)

        call_kwargs = mock_post.call_args.kwargs
        if 'headers' in call_kwargs:
            assert 'X-Tags' not in call_kwargs['headers']


class TestActivityLogIntegration:
    """Test integration with ActivityLog database table."""

    @patch('ntfy_client.requests.post')
    @patch('ntfy_client.log_notification_to_db')
    def test_logs_successful_notification(self, mock_log_db, mock_post):
        """Logs notification send to ActivityLog table on success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {'NTFY_URL': 'http://localhost:8080/test'}):
            send_notification(title='Test', message='Message', priority='high')

        # Should log to database
        mock_log_db.assert_called_once()
        call_args = mock_log_db.call_args

        # Verify log contains relevant information
        assert 'Test' in str(call_args)
        assert 'notification_sent' in str(call_args) or 'type' in call_args.kwargs

    @patch('ntfy_client.requests.post')
    @patch('ntfy_client.log_notification_to_db')
    def test_logs_failed_notification(self, mock_log_db, mock_post):
        """Logs notification failure to ActivityLog table."""
        mock_post.side_effect = requests.ConnectionError('Connection failed')

        with patch.dict(os.environ, {'NTFY_URL': 'http://localhost:8080/test'}):
            send_notification(title='Test', message='Message')

        # Should log the error
        mock_log_db.assert_called_once()
        call_args = mock_log_db.call_args

        # Verify log contains error information
        assert 'error' in str(call_args) or 'notification_error' in str(call_args)
