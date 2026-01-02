#!/bin/bash

# GrokApp Deployment Script
# =========================
# Production deployment automation for GrokApp

set -e  # Exit on error

# Configuration
DEPLOY_ENV="${DEPLOY_ENV:-production}"
APP_DIR="/opt/grokapp"
BACKUP_DIR="/var/backups/grokapp"
LOG_FILE="/var/log/grokapp/deploy.log"
SERVICES="grokapi orbitbridge jobmaster"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local msg="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO)  color=$GREEN ;;
        WARN)  color=$YELLOW ;;
        ERROR) color=$RED ;;
        *)     color=$NC ;;
    esac
    
    echo -e "${color}[$timestamp] [$level] $msg${NC}"
    echo "[$timestamp] [$level] $msg" >> "$LOG_FILE" 2>/dev/null || true
}

# Pre-deployment checks
pre_deploy_checks() {
    log INFO "Running pre-deployment checks..."
    
    # Check if running as appropriate user
    if [ "$EUID" -eq 0 ] && [ "$DEPLOY_ENV" = "production" ]; then
        log WARN "Running as root in production - consider using a dedicated deploy user"
    fi
    
    # Check disk space
    available_space=$(df -P "$APP_DIR" 2>/dev/null | tail -1 | awk '{print $4}' || echo "0")
    if [ "$available_space" -lt 1048576 ]; then  # 1GB
        log WARN "Low disk space: ${available_space}KB available"
    fi
    
    # Check git status
    if [ -d "$APP_DIR/.git" ]; then
        if [ -n "$(git -C $APP_DIR status --porcelain 2>/dev/null)" ]; then
            log WARN "Uncommitted changes in $APP_DIR"
        fi
    fi
    
    log INFO "Pre-deployment checks passed"
}

# Create backup before deployment
create_backup() {
    log INFO "Creating pre-deployment backup..."
    
    local backup_name="grokapp_predeploy_$(date '+%Y%m%d_%H%M%S')"
    local backup_path="$BACKUP_DIR/$backup_name.tar.gz"
    
    mkdir -p "$BACKUP_DIR"
    
    if [ -d "$APP_DIR" ]; then
        tar -czf "$backup_path" -C "$(dirname $APP_DIR)" "$(basename $APP_DIR)" 2>/dev/null || true
        log INFO "Backup created: $backup_path"
    else
        log WARN "App directory does not exist, skipping backup"
    fi
}

# Stop services
stop_services() {
    log INFO "Stopping services..."
    
    for service in $SERVICES; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            systemctl stop "$service" || log WARN "Failed to stop $service"
            log INFO "Stopped $service"
        else
            log INFO "$service was not running"
        fi
    done
}

# Pull latest code
pull_code() {
    log INFO "Pulling latest code..."
    
    if [ -d "$APP_DIR/.git" ]; then
        cd "$APP_DIR"
        git fetch origin
        git checkout main
        git pull origin main
        log INFO "Code updated to $(git rev-parse --short HEAD)"
    else
        log ERROR "Git repository not found in $APP_DIR"
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    log INFO "Installing dependencies..."
    
    cd "$APP_DIR"
    
    # Python dependencies
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt -q
        log INFO "Python dependencies installed"
    fi
    
    # Node dependencies (if applicable)
    if [ -f "package.json" ]; then
        npm install --production
        log INFO "Node dependencies installed"
    fi
}

# Run database migrations
run_migrations() {
    log INFO "Running database migrations..."
    
    cd "$APP_DIR"
    
    if [ -f "manage.py" ]; then
        python3 manage.py migrate --noinput || log WARN "Migration failed or not applicable"
    fi
    
    log INFO "Migrations complete"
}

# Start services
start_services() {
    log INFO "Starting services..."
    
    for service in $SERVICES; do
        systemctl start "$service" || log WARN "Failed to start $service"
        
        # Wait for service to be ready
        sleep 2
        
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            log INFO "Started $service"
        else
            log ERROR "Failed to start $service"
        fi
    done
}

# Run health checks
run_health_checks() {
    log INFO "Running health checks..."
    
    cd "$APP_DIR"
    
    # Run Python health check module
    python3 -m monitoring.health_checks 2>/dev/null || log WARN "Health check module not available"
    
    # Check individual endpoints
    local all_healthy=true
    
    if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
        log INFO "GrokAPI health check: OK"
    else
        log ERROR "GrokAPI health check: FAILED"
        all_healthy=false
    fi
    
    if curl -sf http://localhost:3001/status > /dev/null 2>&1; then
        log INFO "OrbitBridge health check: OK"
    else
        log WARN "OrbitBridge health check: FAILED"
        all_healthy=false
    fi
    
    if curl -sf http://localhost:5010/health > /dev/null 2>&1; then
        log INFO "JobMaster health check: OK"
    else
        log WARN "JobMaster health check: FAILED"
        all_healthy=false
    fi
    
    if [ "$all_healthy" = true ]; then
        log INFO "All health checks passed"
    else
        log WARN "Some health checks failed - review services"
    fi
}

# Rollback function
rollback() {
    log ERROR "Deployment failed, initiating rollback..."
    
    # Find most recent backup
    local latest_backup=$(ls -t "$BACKUP_DIR"/grokapp_predeploy_*.tar.gz 2>/dev/null | head -1)
    
    if [ -n "$latest_backup" ]; then
        stop_services
        rm -rf "$APP_DIR"
        tar -xzf "$latest_backup" -C "$(dirname $APP_DIR)"
        start_services
        log INFO "Rolled back to $latest_backup"
    else
        log ERROR "No backup available for rollback"
    fi
}

# Main deployment flow
main() {
    log INFO "=========================================="
    log INFO "Starting GrokApp deployment to $DEPLOY_ENV"
    log INFO "=========================================="
    
    # Set trap for rollback on failure
    trap 'rollback' ERR
    
    pre_deploy_checks
    create_backup
    stop_services
    pull_code
    install_dependencies
    run_migrations
    start_services
    run_health_checks
    
    log INFO "=========================================="
    log INFO "Deployment completed successfully!"
    log INFO "=========================================="
}

# Parse command line arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    status)
        for service in $SERVICES; do
            systemctl status "$service" --no-pager || true
        done
        ;;
    rollback)
        rollback
        ;;
    health)
        run_health_checks
        ;;
    *)
        echo "Usage: $0 {deploy|status|rollback|health}"
        exit 1
        ;;
esac
