#!/usr/bin/env python3
"""
System Monitor Agent
A realistic monitoring tool that demonstrates the complete GitLab Melange pipeline
"""

import json
import os
import sys
import time
import subprocess
import argparse
from datetime import datetime

def get_system_info():
    """Collect basic system information"""
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        
        # Parse memory info
        mem_total = 0
        mem_available = 0
        for line in meminfo.split('\n'):
            if 'MemTotal:' in line:
                mem_total = int(line.split()[1]) * 1024  # Convert KB to bytes
            elif 'MemAvailable:' in line:
                mem_available = int(line.split()[1]) * 1024
        
        mem_used_percent = ((mem_total - mem_available) / mem_total) * 100 if mem_total > 0 else 0
        
        return {
            'memory_total_bytes': mem_total,
            'memory_available_bytes': mem_available,
            'memory_used_percent': round(mem_used_percent, 2)
        }
    except Exception as e:
        return {'error': f'Failed to get memory info: {str(e)}'}

def get_disk_usage():
    """Get disk usage information"""
    try:
        result = subprocess.run(['df', '-B1', '/'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                total = int(parts[1])
                used = int(parts[2])
                available = int(parts[3])
                used_percent = (used / total) * 100 if total > 0 else 0
                
                return {
                    'disk_total_bytes': total,
                    'disk_used_bytes': used,
                    'disk_available_bytes': available,
                    'disk_used_percent': round(used_percent, 2)
                }
        
        return {'error': 'Failed to parse df output'}
    except Exception as e:
        return {'error': f'Failed to get disk usage: {str(e)}'}

def get_cpu_info():
    """Get CPU usage information"""
    try:
        # Read /proc/loadavg for load average
        with open('/proc/loadavg', 'r') as f:
            loadavg = f.read().strip().split()
        
        return {
            'load_1min': float(loadavg[0]),
            'load_5min': float(loadavg[1]),
            'load_15min': float(loadavg[2])
        }
    except Exception as e:
        return {'error': f'Failed to get CPU info: {str(e)}'}

def get_network_info():
    """Get basic network connectivity info"""
    try:
        # Test connectivity to common services
        connectivity = {}
        
        # Test DNS resolution
        result = subprocess.run(['nslookup', 'google.com'], 
                              capture_output=True, text=True, timeout=5)
        connectivity['dns_working'] = result.returncode == 0
        
        # Test internet connectivity
        result = subprocess.run(['ping', '-c', '1', '-W', '3', '8.8.8.8'], 
                              capture_output=True, text=True, timeout=10)
        connectivity['internet_reachable'] = result.returncode == 0
        
        return connectivity
    except Exception as e:
        return {'error': f'Failed to get network info: {str(e)}'}

def check_services():
    """Check status of common services"""
    services = ['sshd', 'systemd-resolved', 'cron']
    service_status = {}
    
    for service in services:
        try:
            result = subprocess.run(['systemctl', 'is-active', service], 
                                  capture_output=True, text=True)
            service_status[service] = result.stdout.strip() == 'active'
        except Exception:
            service_status[service] = False
    
    return service_status

def collect_metrics():
    """Collect all system metrics"""
    timestamp = datetime.now().isoformat()
    hostname = os.uname().nodename
    
    metrics = {
        'timestamp': timestamp,
        'hostname': hostname,
        'system': get_system_info(),
        'disk': get_disk_usage(),
        'cpu': get_cpu_info(),
        'network': get_network_info(),
        'services': check_services()
    }
    
    return metrics

def check_thresholds(metrics):
    """Check if any metrics exceed warning thresholds"""
    warnings = []
    
    # Memory threshold
    if 'memory_used_percent' in metrics['system']:
        if metrics['system']['memory_used_percent'] > 90:
            warnings.append(f"High memory usage: {metrics['system']['memory_used_percent']:.1f}%")
    
    # Disk threshold
    if 'disk_used_percent' in metrics['disk']:
        if metrics['disk']['disk_used_percent'] > 85:
            warnings.append(f"High disk usage: {metrics['disk']['disk_used_percent']:.1f}%")
    
    # Load average threshold (assuming 4 CPU cores)
    if 'load_1min' in metrics['cpu']:
        if metrics['cpu']['load_1min'] > 4.0:
            warnings.append(f"High load average: {metrics['cpu']['load_1min']}")
    
    # Network connectivity
    if 'internet_reachable' in metrics['network']:
        if not metrics['network']['internet_reachable']:
            warnings.append("Internet connectivity issue detected")
    
    # Service checks
    for service, status in metrics['services'].items():
        if not status:
            warnings.append(f"Service {service} is not running")
    
    return warnings

def send_to_monitoring_system(metrics):
    """Send metrics to monitoring system (placeholder)"""
    # In a real implementation, this would send to:
    # - Prometheus pushgateway
    # - CloudWatch
    # - DataDog
    # - Custom monitoring endpoint
    
    monitoring_endpoint = os.environ.get('MONITORING_ENDPOINT')
    if monitoring_endpoint:
        print(f"Would send metrics to: {monitoring_endpoint}")
    else:
        print("No monitoring endpoint configured")

def main():
    parser = argparse.ArgumentParser(description='System Monitor Agent')
    parser.add_argument('--output', choices=['json', 'human'], default='human',
                       help='Output format')
    parser.add_argument('--log-file', help='Log file path')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon (continuous monitoring)')
    parser.add_argument('--interval', type=int, default=60,
                       help='Monitoring interval in seconds (daemon mode)')
    
    args = parser.parse_args()
    
    def run_monitoring():
        """Single monitoring run"""
        metrics = collect_metrics()
        warnings = check_thresholds(metrics)
        
        if args.output == 'json':
            output = {
                'metrics': metrics,
                'warnings': warnings,
                'status': 'warning' if warnings else 'ok'
            }
            print(json.dumps(output, indent=2))
        else:
            # Human readable output
            print(f"System Monitor Report - {metrics['timestamp']}")
            print(f"Hostname: {metrics['hostname']}")
            print()
            
            # System info
            if 'memory_used_percent' in metrics['system']:
                print(f"Memory Usage: {metrics['system']['memory_used_percent']:.1f}%")
            
            if 'disk_used_percent' in metrics['disk']:
                print(f"Disk Usage: {metrics['disk']['disk_used_percent']:.1f}%")
            
            if 'load_1min' in metrics['cpu']:
                print(f"Load Average: {metrics['cpu']['load_1min']:.2f}")
            
            print(f"Internet Connectivity: {'OK' if metrics['network'].get('internet_reachable') else 'FAILED'}")
            
            # Service status
            print("\nService Status:")
            for service, status in metrics['services'].items():
                status_text = 'RUNNING' if status else 'STOPPED'
                print(f"  {service}: {status_text}")
            
            # Warnings
            if warnings:
                print("\nWARNINGS:")
                for warning in warnings:
                    print(f"  - {warning}")
            else:
                print("\nAll systems normal")
        
        # Log to file if specified
        if args.log_file:
            with open(args.log_file, 'a') as f:
                log_entry = {
                    'timestamp': metrics['timestamp'],
                    'hostname': metrics['hostname'],
                    'warnings': warnings,
                    'memory_percent': metrics['system'].get('memory_used_percent'),
                    'disk_percent': metrics['disk'].get('disk_used_percent'),
                    'load_avg': metrics['cpu'].get('load_1min')
                }
                f.write(json.dumps(log_entry) + '\n')
        
        # Send to monitoring system
        send_to_monitoring_system(metrics)
        
        # Return exit code based on warnings
        return 1 if warnings else 0
    
    if args.daemon:
        print(f"Starting system monitor daemon (interval: {args.interval}s)")
        try:
            while True:
                run_monitoring()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nDaemon stopped")
            return 0
    else:
        return run_monitoring()

if __name__ == '__main__':
    sys.exit(main())
