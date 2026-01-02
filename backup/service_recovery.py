"""
GrokApp Service Recovery Scripts
================================
Automated service recovery and health restoration procedures.
"""

import os
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class ServiceRecovery:
    """
    Handles automated service recovery for GrokApp components.
    
    Supported services:
    - GrokAPI (port 8080)
    - OrbitBridge (port 3001)
    - JobMaster (port 5010)
    - Prometheus (port 9090)
    """
    
    def __init__(self):
        self.services = {
            'GrokAPI': {
                'port': 8080,
                'start_cmd': 'python3 -m grokapi.server',
                'health_endpoint': '/health',
                'restart_delay': 5
            },
            'OrbitBridge': {
                'port': 3001,
                'start_cmd': 'node orbitbridge/server.js',
                'health_endpoint': '/status',
                'restart_delay': 3
            },
            'JobMaster': {
                'port': 5010,
                'start_cmd': 'python3 -m jobmaster.server',
                'health_endpoint': '/health',
                'restart_delay': 5
            },
            'Prometheus': {
                'port': 9090,
                'start_cmd': 'prometheus --config.file=prometheus.yml',
                'health_endpoint': '/-/healthy',
                'restart_delay': 10
            }
        }
        
        self.recovery_log: List[Dict] = []
    
    def check_service_port(self, port: int) -> bool:
        """Check if a service is listening on the given port."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def get_service_status(self, service_name: str) -> Dict:
        """Get detailed status of a service."""
        if service_name not in self.services:
            return {'error': f'Unknown service: {service_name}'}
        
        config = self.services[service_name]
        is_running = self.check_service_port(config['port'])
        
        return {
            'service': service_name,
            'port': config['port'],
            'running': is_running,
            'health_endpoint': config['health_endpoint'],
            'checked_at': datetime.utcnow().isoformat() + 'Z'
        }
    
    def get_all_statuses(self) -> Dict[str, Dict]:
        """Get status of all registered services."""
        return {name: self.get_service_status(name) for name in self.services}
    
    def attempt_restart(self, service_name: str, dry_run: bool = True) -> Dict:
        """
        Attempt to restart a failed service.
        
        Args:
            service_name: Name of the service to restart
            dry_run: If True, only log what would happen
            
        Returns:
            Result of the restart attempt
        """
        if service_name not in self.services:
            return {'success': False, 'error': f'Unknown service: {service_name}'}
        
        config = self.services[service_name]
        
        result = {
            'service': service_name,
            'action': 'restart',
            'dry_run': dry_run,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        if dry_run:
            result['message'] = f"Would execute: {config['start_cmd']}"
            result['success'] = True
        else:
            try:
                # In production, this would actually restart the service
                # For safety, we only log the command
                print(f"🔄 Restarting {service_name}...")
                print(f"   Command: {config['start_cmd']}")
                print(f"   Waiting {config['restart_delay']}s for startup...")
                
                # Simulate restart delay
                time.sleep(1)  # Reduced for testing
                
                # Check if it came back up
                is_running = self.check_service_port(config['port'])
                result['success'] = is_running
                result['running_after'] = is_running
                
            except Exception as e:
                result['success'] = False
                result['error'] = str(e)
        
        # Log recovery attempt
        self.recovery_log.append(result)
        
        return result
    
    def run_recovery_playbook(self, failed_services: List[str]) -> Dict:
        """
        Execute recovery playbook for multiple failed services.
        
        Args:
            failed_services: List of service names that need recovery
            
        Returns:
            Summary of recovery actions
        """
        print(f"📋 Running recovery playbook for {len(failed_services)} services")
        
        results = {
            'started_at': datetime.utcnow().isoformat() + 'Z',
            'services_targeted': failed_services,
            'recovery_results': [],
            'overall_success': True
        }
        
        for service in failed_services:
            print(f"\n{'='*40}")
            print(f"Recovering: {service}")
            
            # Step 1: Verify service is actually down
            status = self.get_service_status(service)
            if status.get('running', False):
                print(f"  ✅ {service} is already running, skipping")
                results['recovery_results'].append({
                    'service': service,
                    'action': 'skipped',
                    'reason': 'already_running'
                })
                continue
            
            # Step 2: Attempt restart
            restart_result = self.attempt_restart(service, dry_run=True)
            results['recovery_results'].append(restart_result)
            
            if not restart_result.get('success', False):
                results['overall_success'] = False
        
        results['completed_at'] = datetime.utcnow().isoformat() + 'Z'
        
        # Summary
        print(f"\n{'='*40}")
        print("📊 Recovery Playbook Summary:")
        print(f"   Services targeted: {len(failed_services)}")
        print(f"   Overall success: {results['overall_success']}")
        
        return results
    
    def get_recovery_history(self) -> List[Dict]:
        """Get history of all recovery attempts."""
        return self.recovery_log


class RollbackManager:
    """
    Manages application rollbacks to previous known-good states.
    """
    
    def __init__(self, app_dir: str):
        self.app_dir = Path(app_dir)
        self.rollback_history: List[Dict] = []
    
    def get_git_history(self, count: int = 5) -> List[Dict]:
        """Get recent git commits for potential rollback."""
        try:
            result = subprocess.run(
                ['git', 'log', f'-{count}', '--pretty=format:%H|%s|%ai'],
                cwd=self.app_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if '|' in line:
                    parts = line.split('|')
                    commits.append({
                        'sha': parts[0],
                        'message': parts[1] if len(parts) > 1 else '',
                        'date': parts[2] if len(parts) > 2 else ''
                    })
            
            return commits
            
        except Exception as e:
            print(f"Error getting git history: {e}")
            return []
    
    def rollback_to_commit(self, commit_sha: str, dry_run: bool = True) -> Dict:
        """
        Rollback application to a specific commit.
        
        Args:
            commit_sha: Git commit SHA to rollback to
            dry_run: If True, only show what would happen
            
        Returns:
            Rollback result
        """
        result = {
            'commit': commit_sha,
            'dry_run': dry_run,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        if dry_run:
            print(f"🔄 [DRY RUN] Would rollback to: {commit_sha[:8]}")
            result['success'] = True
            result['message'] = f"Would execute: git checkout {commit_sha}"
        else:
            try:
                # Create backup branch first
                backup_branch = f"pre_rollback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                
                subprocess.run(
                    ['git', 'branch', backup_branch],
                    cwd=self.app_dir,
                    check=True
                )
                
                subprocess.run(
                    ['git', 'checkout', commit_sha],
                    cwd=self.app_dir,
                    check=True
                )
                
                result['success'] = True
                result['backup_branch'] = backup_branch
                
            except subprocess.CalledProcessError as e:
                result['success'] = False
                result['error'] = str(e)
        
        self.rollback_history.append(result)
        return result


# Example usage
if __name__ == "__main__":
    print("🔧 GrokApp Service Recovery System")
    print("=" * 50)
    
    recovery = ServiceRecovery()
    
    # Check all service statuses
    print("\n📊 Current Service Status:")
    for name, status in recovery.get_all_statuses().items():
        icon = "✅" if status.get('running', False) else "❌"
        print(f"   {icon} {name}: {'ONLINE' if status.get('running') else 'OFFLINE'}")
    
    # Simulate recovery for offline services
    offline = [name for name, status in recovery.get_all_statuses().items() 
               if not status.get('running', False)]
    
    if offline:
        print(f"\n⚠️ Found {len(offline)} offline services")
        recovery.run_recovery_playbook(offline)
    else:
        print("\n✅ All services are running")
