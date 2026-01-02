"""
GrokApp Tests for Disaster Recovery Module
==========================================
"""

import pytest
import tempfile
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from backup.disaster_recovery import DisasterRecoveryManager


class TestDisasterRecoveryManager:
    """Tests for DisasterRecoveryManager class."""
    
    def test_initialization(self):
        """Test DR manager initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'backup_dir': tmpdir}
            dr = DisasterRecoveryManager(config=config)
            
            assert dr is not None
            assert dr.backup_dir == Path(tmpdir)
    
    def test_default_config(self):
        """Test default configuration is applied."""
        dr = DisasterRecoveryManager()
        
        assert 'retention_days' in dr.config
        assert 'max_backups' in dr.config
        assert 'critical_paths' in dr.config
    
    def test_create_backup(self):
        """Test creating a backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'backup_dir': tmpdir, 'critical_paths': []}
            dr = DisasterRecoveryManager(config=config)
            
            backup = dr.create_backup(backup_type='test')
            
            assert backup['status'] == 'completed'
            assert 'backup_id' in backup
            assert 'checksum_sha256' in backup
            assert backup['backup_type'] == 'test'
    
    def test_list_backups(self):
        """Test listing backups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'backup_dir': tmpdir, 'critical_paths': []}
            dr = DisasterRecoveryManager(config=config)
            
            # Create a few backups
            dr.create_backup(backup_type='test1')
            dr.create_backup(backup_type='test2')
            
            backups = dr.list_backups()
            
            assert len(backups) == 2
    
    def test_verify_backup(self):
        """Test backup verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'backup_dir': tmpdir, 'critical_paths': []}
            dr = DisasterRecoveryManager(config=config)
            
            backup = dr.create_backup(backup_type='test')
            
            result = dr.verify_backup(backup['backup_id'])
            
            assert result is True
    
    def test_verify_nonexistent_backup(self):
        """Test verifying a non-existent backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'backup_dir': tmpdir}
            dr = DisasterRecoveryManager(config=config)
            
            result = dr.verify_backup('nonexistent_backup')
            
            assert result is False
    
    def test_get_recovery_status(self):
        """Test getting recovery status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'backup_dir': tmpdir, 'critical_paths': []}
            dr = DisasterRecoveryManager(config=config)
            
            # No backups yet
            status = dr.get_recovery_status()
            assert status['status'] == 'no_backups'
            
            # Create a backup
            dr.create_backup(backup_type='test')
            
            status = dr.get_recovery_status()
            assert status['status'] == 'healthy'
            assert status['total_backups'] == 1
    
    def test_backup_metadata_saved(self):
        """Test that backup metadata is saved correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'backup_dir': tmpdir, 'critical_paths': []}
            dr = DisasterRecoveryManager(config=config)
            
            backup = dr.create_backup(backup_type='test')
            
            metadata_path = Path(tmpdir) / f"{backup['backup_id']}_metadata.json"
            assert metadata_path.exists()
            
            with open(metadata_path, 'r') as f:
                saved_metadata = json.load(f)
            
            assert saved_metadata['backup_id'] == backup['backup_id']
            assert saved_metadata['checksum_sha256'] == backup['checksum_sha256']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
