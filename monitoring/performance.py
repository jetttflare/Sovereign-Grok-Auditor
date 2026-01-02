"""
GrokApp Performance Tuning Module
=================================
Performance monitoring, profiling, and optimization utilities.
"""

import time
import functools
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class PerformanceMetric:
    """Single performance measurement."""
    name: str
    duration_ms: float
    timestamp: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class PerformanceProfile:
    """Aggregated performance profile."""
    name: str
    call_count: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


class PerformanceMonitor:
    """
    Production-grade performance monitoring for GrokApp.
    
    Features:
    - Function timing decorator
    - Percentile calculations
    - Performance profiles
    - Slow query detection
    - Memory tracking
    """
    
    def __init__(self, slow_threshold_ms: float = 1000.0):
        """
        Initialize performance monitor.
        
        Args:
            slow_threshold_ms: Threshold for slow operation warnings
        """
        self.slow_threshold_ms = slow_threshold_ms
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.slow_operations: List[PerformanceMetric] = []
        self.enabled = True
        
    def timer(self, name: Optional[str] = None):
        """
        Decorator to time function execution.
        
        Usage:
            @perf.timer()
            def my_function():
                pass
                
            @perf.timer("custom_name")
            def another_function():
                pass
        """
        def decorator(func: Callable) -> Callable:
            metric_name = name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                if not self.enabled:
                    return func(*args, **kwargs)
                
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.perf_counter()
                    duration_ms = (end_time - start_time) * 1000
                    self.record(metric_name, duration_ms)
            
            return wrapper
        return decorator
    
    def record(self, name: str, duration_ms: float, metadata: Dict = None):
        """Record a performance measurement."""
        self.metrics[name].append(duration_ms)
        
        # Check for slow operation
        if duration_ms > self.slow_threshold_ms:
            self.slow_operations.append(PerformanceMetric(
                name=name,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow().isoformat() + 'Z',
                metadata=metadata or {}
            ))
            print(f"⚠️ SLOW OPERATION: {name} took {duration_ms:.2f}ms")
    
    def get_profile(self, name: str) -> Optional[PerformanceProfile]:
        """Get performance profile for a specific metric."""
        if name not in self.metrics or not self.metrics[name]:
            return None
        
        measurements = self.metrics[name]
        sorted_measurements = sorted(measurements)
        n = len(measurements)
        
        return PerformanceProfile(
            name=name,
            call_count=n,
            total_time_ms=sum(measurements),
            avg_time_ms=statistics.mean(measurements),
            min_time_ms=min(measurements),
            max_time_ms=max(measurements),
            p50_ms=sorted_measurements[int(n * 0.50)] if n > 0 else 0,
            p95_ms=sorted_measurements[int(n * 0.95)] if n > 0 else 0,
            p99_ms=sorted_measurements[int(n * 0.99)] if n > 0 else 0
        )
    
    def get_all_profiles(self) -> Dict[str, PerformanceProfile]:
        """Get performance profiles for all tracked metrics."""
        return {name: self.get_profile(name) for name in self.metrics}
    
    def get_slow_operations(self, limit: int = 100) -> List[PerformanceMetric]:
        """Get recent slow operations."""
        return self.slow_operations[-limit:]
    
    def clear(self):
        """Clear all metrics."""
        self.metrics.clear()
        self.slow_operations.clear()
    
    def report(self) -> str:
        """Generate a human-readable performance report."""
        lines = [
            "=" * 60,
            "GrokApp Performance Report",
            f"Generated: {datetime.utcnow().isoformat()}Z",
            "=" * 60,
            ""
        ]
        
        profiles = self.get_all_profiles()
        
        if not profiles:
            lines.append("No performance data collected.")
            return "\n".join(lines)
        
        # Sort by total time descending
        sorted_profiles = sorted(
            profiles.items(),
            key=lambda x: x[1].total_time_ms if x[1] else 0,
            reverse=True
        )
        
        lines.append(f"{'Metric':<40} {'Calls':>8} {'Avg(ms)':>10} {'P95(ms)':>10} {'P99(ms)':>10}")
        lines.append("-" * 80)
        
        for name, profile in sorted_profiles:
            if profile:
                lines.append(
                    f"{name[:40]:<40} {profile.call_count:>8} "
                    f"{profile.avg_time_ms:>10.2f} {profile.p95_ms:>10.2f} "
                    f"{profile.p99_ms:>10.2f}"
                )
        
        # Slow operations summary
        if self.slow_operations:
            lines.extend([
                "",
                f"⚠️ Slow Operations (>{self.slow_threshold_ms}ms): {len(self.slow_operations)} total",
                ""
            ])
            
            for op in self.slow_operations[-5:]:  # Last 5
                lines.append(f"  - {op.name}: {op.duration_ms:.2f}ms at {op.timestamp}")
        
        return "\n".join(lines)
    
    def export_json(self, filepath: str):
        """Export performance data to JSON file."""
        data = {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'slow_threshold_ms': self.slow_threshold_ms,
            'profiles': {},
            'slow_operations': []
        }
        
        for name, profile in self.get_all_profiles().items():
            if profile:
                data['profiles'][name] = {
                    'call_count': profile.call_count,
                    'total_time_ms': profile.total_time_ms,
                    'avg_time_ms': profile.avg_time_ms,
                    'min_time_ms': profile.min_time_ms,
                    'max_time_ms': profile.max_time_ms,
                    'p50_ms': profile.p50_ms,
                    'p95_ms': profile.p95_ms,
                    'p99_ms': profile.p99_ms
                }
        
        for op in self.slow_operations:
            data['slow_operations'].append({
                'name': op.name,
                'duration_ms': op.duration_ms,
                'timestamp': op.timestamp,
                'metadata': op.metadata
            })
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


class CacheManager:
    """
    Simple in-memory cache with TTL support for performance optimization.
    """
    
    def __init__(self, default_ttl_seconds: int = 300):
        self.default_ttl = default_ttl_seconds
        self.cache: Dict[str, Dict] = {}
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        if time.time() > entry['expires_at']:
            del self.cache[key]
            self.misses += 1
            return None
        
        self.hits += 1
        return entry['value']
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set value in cache with TTL."""
        ttl = ttl_seconds or self.default_ttl
        self.cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }
    
    def delete(self, key: str):
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """Clear entire cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        return {
            'size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.hits / total if total > 0 else 0
        }


class ConnectionPool:
    """
    Simple connection pool for database/HTTP connections.
    """
    
    def __init__(self, max_size: int = 10, create_func: Callable = None):
        self.max_size = max_size
        self.create_func = create_func or (lambda: None)
        self.pool: List[Any] = []
        self.in_use: int = 0
        
    def acquire(self) -> Any:
        """Acquire a connection from the pool."""
        if self.pool:
            self.in_use += 1
            return self.pool.pop()
        
        if self.in_use < self.max_size:
            self.in_use += 1
            return self.create_func()
        
        raise Exception("Connection pool exhausted")
    
    def release(self, conn: Any):
        """Release a connection back to the pool."""
        if len(self.pool) < self.max_size:
            self.pool.append(conn)
        self.in_use = max(0, self.in_use - 1)
    
    def get_status(self) -> Dict:
        """Get pool status."""
        return {
            'max_size': self.max_size,
            'available': len(self.pool),
            'in_use': self.in_use
        }


# Global performance monitor instance
perf = PerformanceMonitor(slow_threshold_ms=500.0)

# Global cache instance
cache = CacheManager(default_ttl_seconds=300)


# Example usage and testing
if __name__ == "__main__":
    print("🔧 GrokApp Performance Tuning System")
    print("=" * 50)
    
    # Test performance monitor
    @perf.timer("test_operation")
    def simulate_work(duration_ms: float):
        time.sleep(duration_ms / 1000)
        return "done"
    
    # Run some test operations
    print("\n📊 Running test operations...")
    for i in range(10):
        duration = 50 + (i * 20)  # Varying durations
        simulate_work(duration)
    
    # Simulate a slow operation
    simulate_work(600)  # This should trigger slow warning
    
    # Print report
    print("\n" + perf.report())
    
    # Test cache
    print("\n📦 Testing cache...")
    cache.set("user:123", {"name": "JLow", "role": "admin"})
    result = cache.get("user:123")
    print(f"Cache get: {result}")
    print(f"Cache stats: {cache.get_stats()}")
    
    # Export metrics
    perf.export_json("/tmp/grokapp_perf_test.json")
    print("\n✅ Performance data exported to /tmp/grokapp_perf_test.json")
