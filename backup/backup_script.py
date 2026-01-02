import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

class BackupManager:
    def __init__(self, source_dirs=None, backup_vault="/Users/jlow/.gemini/antigravity/scratch/GrokApp/vault/backups"):
        self.source_dirs = source_dirs or [
            "/Users/jlow/.gemini/antigravity/scratch/GrokApp",
            "/Users/jlow/Desktop/OrbitV3Full",
            "/Users/jlow/Desktop/JobMaster"
        ]
        self.backup_vault = Path(backup_vault)
        self.backup_vault.mkdir(parents=True, exist_ok=True)

    def run_backup(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_vault / f"sovereign_backup_{timestamp}.tar.gz"
        
        print(f"📦 Starting Collective Backup to {backup_file}...")
        
        with tarfile.open(backup_file, "w:gz") as tar:
            for source in self.source_dirs:
                source_path = Path(source)
                if source_path.exists():
                    print(f"  Adding {source_path.name}...")
                    # Exclude node_modules and .git for space efficiency
                    def exclude_large(tarinfo):
                        if "node_modules" in tarinfo.name or ".git" in tarinfo.name or "DerivedData" in tarinfo.name:
                            return None
                        return tarinfo
                    tar.add(source, arcname=source_path.name, filter=exclude_large)
        
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        print(f"✅ Backup Complete. Size: {size_mb:.2f} MB")
        return backup_file

if __name__ == "__main__":
    bm = BackupManager()
    bm.run_backup()
