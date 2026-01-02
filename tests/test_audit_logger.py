"""
GrokApp Audit Logger Tests
==========================
Unit tests for the security/audit_logger.py module.
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from security.audit_logger import AuditLogger


class TestAuditLogger:
    """Test suite for AuditLogger class."""

    def test_initialization(self):
        """Test AuditLogger initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            assert logger is not None
            assert logger.log_dir == Path(tmpdir)

    def test_log_dir_created(self):
        """Test that log directory is created on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_subdir = Path(tmpdir) / 'audit_logs'
            logger = AuditLogger(log_dir=str(log_subdir))
            assert log_subdir.exists()

    def test_log_event_creates_entry(self):
        """Test that log_event() creates a log entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            logger.log_event(
                user_id='test_user',
                action='TEST_ACTION',
                resource='TEST_RESOURCE',
                result='SUCCESS',
                severity='INFO'
            )
            
            # Check that log file was created
            log_files = list(Path(tmpdir).glob('*.log'))
            assert len(log_files) >= 1

    def test_log_entry_structure(self):
        """Test that log entries have the correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            logger.log_event(
                user_id='test_user',
                action='TEST_ACTION',
                resource='TEST_RESOURCE',
                result='SUCCESS',
                severity='INFO',
                metadata={'key': 'value'}
            )
            
            # Read the log file
            log_files = list(Path(tmpdir).glob('*.log'))
            assert len(log_files) >= 1
            
            with open(log_files[0], 'r') as f:
                content = f.read()
                # Each line should be valid JSON
                for line in content.strip().split('\n'):
                    if line:
                        entry = json.loads(line)
                        assert 'timestamp' in entry
                        assert 'user_id' in entry
                        assert 'action' in entry
                        assert 'resource' in entry
                        assert 'result' in entry
                        assert 'severity' in entry
                        assert 'metadata' in entry

    def test_severity_levels(self):
        """Test that different severity levels are handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            
            severities = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            for severity in severities:
                logger.log_event(
                    user_id='test_user',
                    action=f'TEST_{severity}',
                    resource='TEST_RESOURCE',
                    result='SUCCESS',
                    severity=severity
                )
            
            # Verify all were logged
            log_files = list(Path(tmpdir).glob('*.log'))
            assert len(log_files) >= 1
            
            with open(log_files[0], 'r') as f:
                lines = [l for l in f.read().strip().split('\n') if l]
                assert len(lines) >= len(severities)

    def test_timestamp_format(self):
        """Test that timestamps are in ISO format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            logger.log_event(
                user_id='test_user',
                action='TEST_ACTION',
                resource='TEST_RESOURCE',
                result='SUCCESS',
                severity='INFO'
            )
            
            log_files = list(Path(tmpdir).glob('*.log'))
            with open(log_files[0], 'r') as f:
                line = f.readline()
                entry = json.loads(line)
                
                # Should be parseable as ISO datetime
                try:
                    datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                except ValueError:
                    pytest.fail(f"Invalid timestamp format: {entry['timestamp']}")

    def test_special_characters_in_log(self):
        """Test that special characters are handled properly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            
            special_chars = 'Test with "quotes", <brackets>, and üñíçødé'
            logger.log_event(
                user_id='test_user',
                action=special_chars,
                resource='TEST_RESOURCE',
                result='SUCCESS',
                severity='INFO'
            )
            
            # Should not raise an exception
            log_files = list(Path(tmpdir).glob('*.log'))
            with open(log_files[0], 'r') as f:
                entry = json.loads(f.readline())
                assert special_chars in entry['action']

    def test_metadata_field_optional(self):
        """Test that metadata field defaults to empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            
            # Log without metadata
            logger.log_event(
                user_id='test_user',
                action='TEST_ACTION',
                resource='TEST_RESOURCE',
                result='SUCCESS',
                severity='INFO'
            )
            
            log_files = list(Path(tmpdir).glob('*.log'))
            with open(log_files[0], 'r') as f:
                entry = json.loads(f.readline())
                assert entry['metadata'] == {}

    def test_metadata_field_with_nested_data(self):
        """Test that nested metadata is properly serialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            
            nested_metadata = {
                'level1': {
                    'level2': {
                        'level3': 'deep_value'
                    }
                },
                'array': [1, 2, 3],
                'mixed': ['a', 1, {'key': 'value'}]
            }
            
            logger.log_event(
                user_id='test_user',
                action='TEST_ACTION',
                resource='TEST_RESOURCE',
                result='SUCCESS',
                severity='INFO',
                metadata=nested_metadata
            )
            
            log_files = list(Path(tmpdir).glob('*.log'))
            with open(log_files[0], 'r') as f:
                entry = json.loads(f.readline())
                assert entry['metadata'] == nested_metadata

    def test_log_security_alert(self):
        """Test the log_security_alert convenience method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            
            logger.log_security_alert(
                reason='Suspicious activity',
                detail='Multiple failed login attempts'
            )
            
            log_files = list(Path(tmpdir).glob('*.log'))
            with open(log_files[0], 'r') as f:
                entry = json.loads(f.readline())
                assert entry['user_id'] == 'SYSTEM'
                assert entry['action'] == 'SECURITY_ALERT'
                assert entry['severity'] == 'CRITICAL'


class TestAuditLoggerSecurity:
    """Security-focused tests for AuditLogger."""

    def test_sensitive_data_in_metadata(self):
        """Test that sensitive data can be logged in metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            
            # Log with potentially sensitive data (logger doesn't filter, app should)
            logger.log_event(
                user_id='test_user',
                action='API_CALL',
                resource='EXTERNAL_API',
                result='SUCCESS',
                severity='INFO',
                metadata={'api_key': 'sk-test-12345'}
            )
            
            # The logger should NOT crash
            log_files = list(Path(tmpdir).glob('*.log'))
            assert len(log_files) >= 1

    def test_log_file_exists(self):
        """Test that log files are created and accessible."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(log_dir=tmpdir)
            logger.log_event(
                user_id='test_user',
                action='TEST_ACTION',
                resource='TEST_RESOURCE',
                result='SUCCESS',
                severity='INFO'
            )
            
            log_files = list(Path(tmpdir).glob('*.log'))
            for log_file in log_files:
                # File should be readable
                assert log_file.exists()
                assert log_file.is_file()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
