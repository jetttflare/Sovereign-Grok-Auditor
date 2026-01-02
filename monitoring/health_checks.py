import requests
import time
import socket
from datetime import datetime

class HealthCheck:
    def __init__(self):
        self.services = {
            "GrokAPI": "http://localhost:8080/health",
            "OrbitBridge": "http://localhost:3001/status",
            "JobMaster": "http://localhost:5010/health"
        }

    def check_local_port(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def run_suite(self):
        print(f"🏥 Starting Operational Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        results = {}
        
        # Check standard ports
        results["OrbitV3_HUD"] = self.check_local_port(3001)
        results["Grok_Auditor"] = self.check_local_port(8085)
        results["Prometheus"] = self.check_local_port(9090)
        
        for name, status in results.items():
            icon = "✅" if status else "❌"
            print(f" {icon} {name}: {'ONLINE' if status else 'OFFLINE'}")
            
        return results

if __name__ == "__main__":
    hc = HealthCheck()
    hc.run_suite()
