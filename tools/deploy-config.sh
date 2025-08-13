#!/bin/bash
"""
Simple Configuration Deployment Tool
What ISVs actually need - deploy config files and restart services
"""

set -e

APP_NAME="myapp"
CONFIG_DIR="/etc/${APP_NAME}"
BACKUP_DIR="/var/backups/${APP_NAME}"
LOG_FILE="/var/log/${APP_NAME}-deploy.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

backup_existing_config() {
    if [ -d "$CONFIG_DIR" ]; then
        log "Backing up existing configuration..."
        mkdir -p "$BACKUP_DIR"
        cp -r "$CONFIG_DIR" "$BACKUP_DIR/config-$(date +%Y%m%d-%H%M%S)"
        log "Backup completed"
    fi
}

deploy_config_files() {
    log "Deploying configuration files..."
    
    # Create config directory
    mkdir -p "$CONFIG_DIR"
    
    # Deploy main app config
    cat > "$CONFIG_DIR/app.conf" << 'EOF'
# Application Configuration
app_name=myapp
app_port=8080
log_level=INFO
database_url=postgresql://localhost:5432/myapp
redis_url=redis://localhost:6379/0
EOF

    # Deploy nginx config
    cat > "$CONFIG_DIR/nginx.conf" << 'EOF'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /health {
        access_log off;
        return 200 "healthy\n";
    }
}
EOF

    # Set proper permissions
    chown -R myapp:myapp "$CONFIG_DIR" 2>/dev/null || true
    chmod 644 "$CONFIG_DIR"/*.conf
    
    log "Configuration files deployed successfully"
}

restart_services() {
    log "Restarting services..."
    
    # Restart application services
    for service in myapp nginx; do
        if systemctl is-enabled "$service" >/dev/null 2>&1; then
            log "Restarting $service..."
            systemctl restart "$service"
            
            # Wait for service to be ready
            sleep 2
            if systemctl is-active "$service" >/dev/null 2>&1; then
                log "$service restarted successfully"
            else
                log "ERROR: $service failed to start"
                exit 1
            fi
        else
            log "Service $service not found or not enabled, skipping"
        fi
    done
}

verify_deployment() {
    log "Verifying deployment..."
    
    # Check if config files exist
    for config_file in app.conf nginx.conf; do
        if [ ! -f "$CONFIG_DIR/$config_file" ]; then
            log "ERROR: Configuration file $config_file not found"
            exit 1
        fi
    done
    
    # Test application health
    if command -v curl >/dev/null 2>&1; then
        if curl -s http://localhost/health >/dev/null; then
            log "Health check passed"
        else
            log "WARNING: Health check failed"
        fi
    fi
    
    log "Deployment verification completed"
}

main() {
    log "Starting configuration deployment for $APP_NAME"
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    backup_existing_config
    deploy_config_files
    restart_services
    verify_deployment
    
    log "Configuration deployment completed successfully"
}

# Run main function
main "$@"
