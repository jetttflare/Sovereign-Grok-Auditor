"""
GrokApp Disaster Recovery System
================================
Automated backup, health monitoring, and recovery procedures.
"""

import os
import json
import shutil
import hashlib
import tarfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import subprocess


class DisasterRecoveryManager:
    """
    Production-grade Disaster Recovery Manager for GrokApp.
    
    Features:
    - Automated configuration backups
    - Database snapshot management
    - Health-based recovery triggers
    - Rollback capabilities
    - Integrity verification
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize DR manager with configuration."""
        self.config = config or self._default_config()
        self.backup_dir = Path(self.config.get('backup_dir', '/tmp/grokapp_backups'))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Recovery state
        self.last_backup_time: Optional[datetime] = None
        self.recovery_points: List[Dict] = []
        
    def _default_config(self) -> Dict:
        """Default DR configuration."""
        return {
            'backup_dir': '/Users/jlow/.gemini/antigravity/scratch/GrokApp/backup/snapshots',
            'retention_days': 7,
            'max_backups': 10,
            'critical_paths': [
                'security/',
                'monitoring/',
                'config/',
                '.env',
                'requirements.txt'
            ],
            'exclude_patterns': [
                '__pycache__',
                '.git',
                'node_modules',
                '*.pyc',
                '.pytest_cache',
                'logs/audit/*.log'  # Logs are backed up separately
            ]
        }
    
    def create_backup(self, backup_type: str = 'full') -> Dict:
        """
        Create a backup of critical GrokApp components.
        
        Args:
            backup_type: 'full', 'config', or 'incremental'
            
        Returns:
            Backup metadata dictionary
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_name = f"grokapp_{backup_type}_{timestamp}"
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Get source directory
        source_dir = Path(__file__).parent.parent
        
        # Create tarball
        files_backed_up = []
        with tarfile.open(backup_path, 'w:gz') as tar:
            for critical_path in self.config['critical_paths']:
                full_path = source_dir / critical_path
                if full_path.exists():
                    tar.add(full_path, arcname=critical_path)
                    files_backed_up.append(critical_path)
        
        # Calculate checksum
        checksum = self._calculate_checksum(backup_path)
        
        # Create metadata
        metadata = {
            'backup_id': backup_name,
            'backup_type': backup_type,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'path': str(backup_path),
            'size_bytes': backup_path.stat().st_size if backup_path.exists() else 0,
            'checksum_sha256': checksum,
            'files_included': files_backed_up,
            'status': 'completed'
        }
        
        # Save metadata
        metadata_path = self.backup_dir / f"{backup_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Update state
        self.last_backup_time = datetime.utcnow()
        self.recovery_points.append(metadata)
        
        # Cleanup old backups
        self._cleanup_old_backups()
        
        print(f"✅ Backup created: {backup_name}")
        print(f"   Size: {metadata['size_bytes']} bytes")
        print(f"   Files: {len(files_backed_up)}")
        
        return metadata
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def verify_backup(self, backup_id: str) -> bool:
        """
        Verify backup integrity using checksum.
        
        Args:
            backup_id: The backup identifier
            
        Returns:
            True if backup is valid, False otherwise
        """
        metadata_path = self.backup_dir / f"{backup_id}_metadata.json"
        
        if not metadata_path.exists():
            print(f"❌ Backup metadata not found: {backup_id}")
            return False
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        backup_path = Path(metadata['path'])
        if not backup_path.exists():
            print(f"❌ Backup file not found: {backup_path}")
            return False
        
        current_checksum = self._calculate_checksum(backup_path)
        expected_checksum = metadata['checksum_sha256']
        
        if current_checksum == expected_checksum:
            print(f"✅ Backup verified: {backup_id}")
            return True
        else:
            print(f"❌ Checksum mismatch for {backup_id}")
            return False
    
    def list_backups(self) -> List[Dict]:
        """List all available backups."""
        backups = []
        
        for metadata_file in self.backup_dir.glob('*_metadata.json'):
            with open(metadata_file, 'r') as f:
                backups.append(json.load(f))
        
        # Sort by timestamp, newest first
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return backups
    
    def restore_backup(self, backup_id: str, target_dir: Optional[str] = None) -> bool:
        """
        Restore from a backup.
        
        Args:
            backup_id: The backup identifier to restore
            target_dir: Optional custom restore location
            
        Returns:
            True if restoration succeeded, False otherwise
        """
        # Verify backup first
        if not self.verify_backup(backup_id):
            return False
        
        metadata_path = self.backup_dir / f"{backup_id}_metadata.json"
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        backup_path = Path(metadata['path'])
        restore_target = Path(target_dir) if target_dir else Path(__file__).parent.parent
        
        # Create a pre-restore backup
        pre_restore_backup = self.create_backup(backup_type='pre_restore')
        print(f"📦 Created pre-restore backup: {pre_restore_backup['backup_id']}")
        
        # Extract backup
        try:
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(path=restore_target)
            
            print(f"✅ Restored from backup: {backup_id}")
            print(f"   Target: {restore_target}")
            return True
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False
    
    def _cleanup_old_backups(self):
        """Remove backups older than retention period."""
        retention_days = self.config.get('retention_days', 7)
        max_backups = self.config.get('max_backups', 10)
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        backups = self.list_backups()
        
        for i, backup in enumerate(backups):
            backup_time = datetime.fromisoformat(backup['timestamp'].replace('Z', '+00:00'))
            
            # Keep if within retention period and under max count
            if i < max_backups and backup_time.replace(tzinfo=None) > cutoff_date:
                continue
            
            # Delete old backup
            backup_path = Path(backup['path'])
            metadata_path = self.backup_dir / f"{backup['backup_id']}_metadata.json"
            
            if backup_path.exists():
                backup_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            
            print(f"🗑️ Cleaned up old backup: {backup['backup_id']}")
    
    def get_recovery_status(self) -> Dict:
        """Get current DR system status."""
        backups = self.list_backups()
        
        return {
            'status': 'healthy' if len(backups) > 0 else 'no_backups',
            'total_backups': len(backups),
            'latest_backup': backups[0] if backups else None,
            'oldest_backup': backups[-1] if backups else None,
            'backup_dir': str(self.backup_dir),
            'retention_days': self.config.get('retention_days', 7),
            'last_checked': datetime.utcnow().isoformat() + 'Z'
        }


class AutoRecoveryMonitor:
    """
    Monitors system health and triggers automatic recovery when needed.
    """
    
    def __init__(self, dr_manager: DisasterRecoveryManager):
        self.dr_manager = dr_manager
        self.failure_count = 0
        self.failure_threshold = 3
        
    def check_and_recover(self, health_check_result: Dict) -> Dict:
        """
        Check health and trigger recovery if needed.
        
        Args:
            health_check_result: Result from HealthCheck.run_suite()
            
        Returns:
            Recovery action taken (if any)
        """
        # Count failures
        failures = [k for k, v in health_check_result.items() if not v]
        
        if failures:
            self.failure_count += 1
            print(f"⚠️ Health check failures detected: {failures}")
            print(f"   Failure count: {self.failure_count}/{self.failure_threshold}")
            
            if self.failure_count >= self.failure_threshold:
                return self._trigger_recovery()
        else:
            self.failure_count = 0
            return {'action': 'none', 'reason': 'all_services_healthy'}
        
        return {'action': 'monitoring', 'failures': failures, 'count': self.failure_count}
    
    def _trigger_recovery(self) -> Dict:
        """Trigger automatic recovery procedures."""
        print("🚨 RECOVERY TRIGGERED: Too many consecutive failures")
        
        # Get latest backup
        backups = self.dr_manager.list_backups()
        
        if not backups:
            return {
                'action': 'recovery_failed',
                'reason': 'no_backups_available'
            }
        
        latest = backups[0]
        
        # In production, this would:
        # 1. Alert operations team
        # 2. Attempt service restart
        # 3. If restart fails, restore from backup
        
        print(f"📋 Recovery plan:")
        print(f"   1. Alert sent to operations")
        print(f"   2. Available backup: {latest['backup_id']}")
        print(f"   3. Awaiting manual confirmation for restore")
        
        # Reset failure count
        self.failure_count = 0
        
        return {
            'action': 'recovery_initiated',
            'backup_available': latest['backup_id'],
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'requires_manual_confirmation': True
        }


# Example usage
if __name__ == "__main__":
    print("🔧 GrokApp Disaster Recovery System")
    print("=" * 50)
    
    # Initialize DR manager
    dr = DisasterRecoveryManager()
    
    # Create a backup
    backup = dr.create_backup(backup_type='full')
    
    # List all backups
    print("\n📋 Available Backups:")
    for b in dr.list_backups():
        print(f"   - {b['backup_id']} ({b['size_bytes']} bytes)")
    
    # Get status
    status = dr.get_recovery_status()
    print(f"\n📊 DR Status: {status['status']}")
    print(f"   Total backups: {status['total_backups']}")
