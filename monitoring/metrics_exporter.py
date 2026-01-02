"""
GrokApp Metrics Exporter
========================
Prometheus-compatible metrics exporter for GrokApp.
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


class MetricsRegistry:
    """
    Registry for Prometheus-compatible metrics.
    
    Supports:
    - Counter: monotonically increasing value
    - Gauge: value that can go up and down
    - Histogram: distribution of values
    """
    
    def __init__(self):
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}
        self.labels: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()
    
    def counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self.counters:
                self.counters[key] = 0
            self.counters[key] += value
            if labels:
                self.labels[key] = labels
    
    def gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self.gauges[key] = value
            if labels:
                self.labels[key] = labels
    
    def histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram observation."""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self.histograms:
                self.histograms[key] = []
            self.histograms[key].append(value)
            if labels:
                self.labels[key] = labels
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create a unique key from metric name and labels."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []
        
        # Export counters
        for key, value in self.counters.items():
            lines.append(f"{key} {value}")
        
        # Export gauges
        for key, value in self.gauges.items():
            lines.append(f"{key} {value}")
        
        # Export histograms (simplified - just sum and count)
        for key, values in self.histograms.items():
            if values:
                lines.append(f"{key}_count {len(values)}")
                lines.append(f"{key}_sum {sum(values)}")
                
                # Buckets
                buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
                for bucket in buckets:
                    count = sum(1 for v in values if v <= bucket)
                    lines.append(f'{key}_bucket{{le="{bucket}"}} {count}')
                lines.append(f'{key}_bucket{{le="+Inf"}} {len(values)}')
        
        return "\n".join(lines)
    
    def export_json(self) -> Dict:
        """Export all metrics as JSON."""
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'histograms': {k: {'count': len(v), 'sum': sum(v), 'avg': sum(v)/len(v) if v else 0} 
                          for k, v in self.histograms.items()}
        }


# Global metrics registry
metrics = MetricsRegistry()


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for metrics endpoint."""
    
    def do_GET(self):
        if self.path == '/metrics':
            content = metrics.export_prometheus()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy'}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress access logs
        pass


def start_metrics_server(port: int = 9101):
    """Start the metrics HTTP server."""
    server = HTTPServer(('0.0.0.0', port), MetricsHandler)
    print(f"📊 Metrics server started on http://localhost:{port}/metrics")
    
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


# Pre-defined application metrics
class AppMetrics:
    """
    Pre-defined metrics for GrokApp.
    """
    
    @staticmethod
    def record_request(method: str, endpoint: str, status_code: int, duration_seconds: float):
        """Record an HTTP request."""
        labels = {'method': method, 'endpoint': endpoint, 'status': str(status_code)}
        metrics.counter('http_requests_total', 1.0, labels)
        metrics.histogram('http_request_duration_seconds', duration_seconds, labels)
    
    @staticmethod
    def record_error(error_type: str, component: str):
        """Record an error occurrence."""
        labels = {'type': error_type, 'component': component}
        metrics.counter('errors_total', 1.0, labels)
    
    @staticmethod
    def record_audit_event(action: str, severity: str):
        """Record an audit log event."""
        labels = {'action': action, 'severity': severity}
        metrics.counter('audit_events_total', 1.0, labels)
    
    @staticmethod
    def set_service_health(service: str, healthy: bool):
        """Set service health status."""
        labels = {'service': service}
        metrics.gauge('service_health', 1.0 if healthy else 0.0, labels)
    
    @staticmethod
    def set_active_connections(service: str, count: int):
        """Set number of active connections."""
        labels = {'service': service}
        metrics.gauge('active_connections', float(count), labels)
    
    @staticmethod
    def record_backup_status(success: bool, size_bytes: int):
        """Record backup operation result."""
        if success:
            metrics.counter('backup_success_total', 1.0)
            metrics.gauge('backup_last_success_timestamp_seconds', time.time())
            metrics.gauge('backup_last_size_bytes', float(size_bytes))
        else:
            metrics.counter('backup_failure_total', 1.0)
        
        metrics.gauge('backup_last_status', 1.0 if success else 0.0)
    
    @staticmethod
    def record_api_call(provider: str, model: str, tokens: int, duration_seconds: float):
        """Record an external API call (LLM, etc)."""
        labels = {'provider': provider, 'model': model}
        metrics.counter('api_calls_total', 1.0, labels)
        metrics.counter('api_tokens_total', float(tokens), labels)
        metrics.histogram('api_call_duration_seconds', duration_seconds, labels)


# Example usage
if __name__ == "__main__":
    print("🔧 GrokApp Metrics Exporter")
    print("=" * 50)
    
    # Start metrics server
    server = start_metrics_server(9101)
    
    # Record some test metrics
    print("\n📊 Recording test metrics...")
    
    AppMetrics.record_request('GET', '/api/health', 200, 0.05)
    AppMetrics.record_request('POST', '/api/audit', 201, 0.12)
    AppMetrics.record_request('GET', '/api/jobs', 200, 0.08)
    AppMetrics.record_request('POST', '/api/audit', 500, 1.5)
    
    AppMetrics.record_error('ConnectionError', 'database')
    AppMetrics.record_error('TimeoutError', 'external_api')
    
    AppMetrics.record_audit_event('LOGIN', 'INFO')
    AppMetrics.record_audit_event('CONFIG_CHANGE', 'WARNING')
    AppMetrics.record_audit_event('SECURITY_ALERT', 'CRITICAL')
    
    AppMetrics.set_service_health('GrokAPI', True)
    AppMetrics.set_service_health('OrbitBridge', True)
    AppMetrics.set_service_health('JobMaster', False)
    
    AppMetrics.record_backup_status(True, 1024 * 1024 * 5)
    
    AppMetrics.record_api_call('gemini', 'gemini-pro', 1500, 2.3)
    AppMetrics.record_api_call('grok', 'grok-1', 800, 1.1)
    
    # Print metrics
    print("\n📈 Prometheus Metrics Output:")
    print("-" * 40)
    print(metrics.export_prometheus())
    
    print("\n✅ Metrics server running at http://localhost:9101/metrics")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
