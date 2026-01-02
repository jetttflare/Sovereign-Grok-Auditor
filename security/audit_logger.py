import json
import os
import time
from datetime import datetime
from pathlib import Path

class AuditLogger:
    def __init__(self, log_dir="/Users/jlow/.gemini/antigravity/scratch/GrokApp/logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"

    def log_event(self, user_id, action, resource, result, severity="INFO", metadata=None):
        """
        Logs a security or operational event.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "result": result,
            "severity": severity,
            "metadata": metadata or {}
        }
        
        log_entry = json.dumps(event)
        
        # Write to local file
        with open(self.current_log_file, "a") as f:
            f.write(log_entry + "\n")
            
        print(f"🛡️ [AUDIT] {severity}: {action} on {resource} by {user_id} -> {result}")
        
    def log_security_alert(self, reason, detail):
        self.log_event("SYSTEM", "SECURITY_ALERT", "FIREWALL", "DETECTED", "CRITICAL", {"reason": reason, "detail": detail})

# Example Usage
if __name__ == "__main__":
    logger = AuditLogger()
    logger.log_event("jlow", "LOGIN", "SYSTEM", "SUCCESS")
    logger.log_event("anonymous", "SSH_ATTEMPT", "SERVER_01", "FAILED", "WARNING")
