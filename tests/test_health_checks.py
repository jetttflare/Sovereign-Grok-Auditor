"""
GrokApp Health Check Tests
==========================
Unit tests for the monitoring/health_checks.py module.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitoring.health_checks import HealthCheck


class TestHealthCheck:
    """Test suite for HealthCheck class."""

    def test_initialization(self):
        """Test HealthCheck initializes with default services."""
        hc = HealthCheck()
        assert hc is not None
        assert hasattr(hc, 'services')
        assert len(hc.services) > 0

    def test_default_services_defined(self):
        """Test that default services are properly defined."""
        hc = HealthCheck()
        
        # Services is a dict with service names as keys
        expected_services = ['GrokAPI', 'OrbitBridge', 'JobMaster']
        for expected in expected_services:
            assert expected in hc.services, f"Missing service: {expected}"

    def test_services_have_urls(self):
        """Test that each service has a health check URL."""
        hc = HealthCheck()
        
        for name, url in hc.services.items():
            assert url.startswith('http'), f"Service {name} has invalid URL: {url}"
            assert '/health' in url or '/status' in url, f"Service {name} missing health endpoint"

    @patch('socket.socket')
    def test_check_local_port_success(self, mock_socket):
        """Test successful port check."""
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 0  # 0 = success
        mock_socket.return_value.__enter__.return_value = mock_sock_instance
        
        hc = HealthCheck()
        result = hc.check_local_port(8080)
        
        assert result is True

    @patch('socket.socket')
    def test_check_local_port_failure(self, mock_socket):
        """Test failed port check."""
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 1  # Non-zero = failure
        mock_socket.return_value.__enter__.return_value = mock_sock_instance
        
        hc = HealthCheck()
        result = hc.check_local_port(8080)
        
        assert result is False

    @patch.object(HealthCheck, 'check_local_port')
    def test_run_suite_returns_dict(self, mock_check):
        """Test that run_suite returns a dictionary."""
        mock_check.return_value = False
        
        hc = HealthCheck()
        results = hc.run_suite()
        
        assert isinstance(results, dict)

    @patch.object(HealthCheck, 'check_local_port')
    def test_run_suite_checks_required_ports(self, mock_check):
        """Test that run_suite checks the expected ports."""
        mock_check.return_value = True
        
        hc = HealthCheck()
        results = hc.run_suite()
        
        # Check that key services are in results
        assert 'OrbitV3_HUD' in results
        assert 'Grok_Auditor' in results
        assert 'Prometheus' in results

    @patch.object(HealthCheck, 'check_local_port')
    def test_run_suite_returns_boolean_statuses(self, mock_check):
        """Test that run_suite returns boolean statuses."""
        mock_check.return_value = True
        
        hc = HealthCheck()
        results = hc.run_suite()
        
        for name, status in results.items():
            assert isinstance(status, bool), f"Status for {name} is not boolean"


class TestHealthCheckIntegration:
    """Integration tests (may require running services)."""

    @pytest.mark.skip(reason="Requires running services")
    def test_real_prometheus_check(self):
        """Test actual Prometheus health check."""
        hc = HealthCheck()
        result = hc.check_local_port(9090)
        # This will only pass if Prometheus is actually running
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
