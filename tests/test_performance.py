"""
GrokApp Tests for Performance Module
====================================
"""

import pytest
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from monitoring.performance import PerformanceMonitor, CacheManager, perf


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class."""
    
    def test_initialization(self):
        """Test monitor initializes correctly."""
        monitor = PerformanceMonitor(slow_threshold_ms=100.0)
        assert monitor.slow_threshold_ms == 100.0
        assert len(monitor.metrics) == 0
    
    def test_record_metric(self):
        """Test recording a metric."""
        monitor = PerformanceMonitor()
        monitor.record("test_metric", 50.0)
        
        assert "test_metric" in monitor.metrics
        assert len(monitor.metrics["test_metric"]) == 1
        assert monitor.metrics["test_metric"][0] == 50.0
    
    def test_slow_operation_detection(self):
        """Test that slow operations are detected."""
        monitor = PerformanceMonitor(slow_threshold_ms=100.0)
        
        monitor.record("fast_op", 50.0)
        monitor.record("slow_op", 150.0)
        
        assert len(monitor.slow_operations) == 1
        assert monitor.slow_operations[0].name == "slow_op"
    
    def test_timer_decorator(self):
        """Test the timer decorator."""
        monitor = PerformanceMonitor()
        
        @monitor.timer("decorated_function")
        def sample_function():
            time.sleep(0.01)
            return "result"
        
        result = sample_function()
        
        assert result == "result"
        assert "decorated_function" in monitor.metrics
        assert len(monitor.metrics["decorated_function"]) == 1
        assert monitor.metrics["decorated_function"][0] >= 10  # At least 10ms
    
    def test_get_profile(self):
        """Test getting a performance profile."""
        monitor = PerformanceMonitor()
        
        for i in range(10):
            monitor.record("profiled_metric", 10.0 + i)
        
        profile = monitor.get_profile("profiled_metric")
        
        assert profile is not None
        assert profile.call_count == 10
        assert profile.min_time_ms == 10.0
        assert profile.max_time_ms == 19.0
        assert profile.avg_time_ms == 14.5
    
    def test_get_profile_missing_metric(self):
        """Test getting profile for non-existent metric."""
        monitor = PerformanceMonitor()
        profile = monitor.get_profile("nonexistent")
        assert profile is None
    
    def test_clear(self):
        """Test clearing metrics."""
        monitor = PerformanceMonitor()
        monitor.record("test", 100.0)
        monitor.clear()
        
        assert len(monitor.metrics) == 0
        assert len(monitor.slow_operations) == 0


class TestCacheManager:
    """Tests for CacheManager class."""
    
    def test_initialization(self):
        """Test cache initializes correctly."""
        cache = CacheManager(default_ttl_seconds=60)
        assert cache.default_ttl == 60
        assert len(cache.cache) == 0
    
    def test_set_and_get(self):
        """Test setting and getting values."""
        cache = CacheManager()
        
        cache.set("key1", "value1")
        result = cache.get("key1")
        
        assert result == "value1"
    
    def test_get_missing_key(self):
        """Test getting a missing key."""
        cache = CacheManager()
        result = cache.get("missing")
        
        assert result is None
        assert cache.misses == 1
    
    def test_cache_expiration(self):
        """Test that cache entries expire."""
        cache = CacheManager()
        
        cache.set("expiring", "value", ttl_seconds=1)
        
        # Should be there immediately
        assert cache.get("expiring") == "value"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be gone
        assert cache.get("expiring") is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = CacheManager()
        
        cache.set("key", "value")
        cache.get("key")  # hit
        cache.get("key")  # hit
        cache.get("missing")  # miss
        
        stats = cache.get_stats()
        
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 2/3
    
    def test_delete(self):
        """Test deleting a key."""
        cache = CacheManager()
        
        cache.set("key", "value")
        cache.delete("key")
        
        assert cache.get("key") is None
    
    def test_clear(self):
        """Test clearing cache."""
        cache = CacheManager()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
