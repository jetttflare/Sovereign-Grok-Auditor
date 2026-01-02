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
        service_names = [s['name'] for s in hc.services]
        
        # At minimum, these core services should exist
        expected_services = ['OrbitBridge', 'GrokAPI', 'JobMaster', 'Prometheus']
        for expected in expected_services:
            assert expected in service_names, f"Missing service: {expected}"

    def test_service_has_required_fields(self):
        """Test that each service has required configuration fields."""
        hc = HealthCheck()
        required_fields = ['name', 'port', 'endpoint']
        
        for service in hc.services:
            for field in required_fields:
                assert field in service, f"Service {service.get('name', 'unknown')} missing field: {field}"

    @patch('socket.socket')
    def test_check_port_success(self, mock_socket):
        """Test successful port check."""
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 0  # 0 = success
        mock_socket.return_value.__enter__.return_value = mock_sock_instance
        
        hc = HealthCheck()
        result = hc.check_port('localhost', 8080)
        
        assert result is True

    @patch('socket.socket')
    def test_check_port_failure(self, mock_socket):
        """Test failed port check."""
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 1  # Non-zero = failure
        mock_socket.return_value.__enter__.return_value = mock_sock_instance
        
        hc = HealthCheck()
        result = hc.check_port('localhost', 8080)
        
        assert result is False

    def test_run_all_checks_returns_dict(self):
        """Test that run_all_checks returns a dictionary."""
        hc = HealthCheck()
        
        with patch.object(hc, 'check_port', return_value=False):
            results = hc.run_all_checks()
        
        assert isinstance(results, dict)
        assert 'services' in results
        assert 'timestamp' in results

    def test_run_all_checks_includes_all_services(self):
        """Test that run_all_checks includes results for all services."""
        hc = HealthCheck()
        
        with patch.object(hc, 'check_port', return_value=False):
            results = hc.run_all_checks()
        
        assert len(results['services']) == len(hc.services)

    def test_check_result_structure(self):
        """Test that each check result has the required structure."""
        hc = HealthCheck()
        
        with patch.object(hc, 'check_port', return_value=True):
            results = hc.run_all_checks()
        
        for service_result in results['services']:
            assert 'name' in service_result
            assert 'status' in service_result
            assert 'port' in service_result
            assert service_result['status'] in ['healthy', 'unhealthy']


class TestHealthCheckIntegration:
    """Integration tests (may require running services)."""

    @pytest.mark.skip(reason="Requires running services")
    def test_real_prometheus_check(self):
        """Test actual Prometheus health check."""
        hc = HealthCheck()
        result = hc.check_port('localhost', 9090)
        # This will only pass if Prometheus is actually running
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
