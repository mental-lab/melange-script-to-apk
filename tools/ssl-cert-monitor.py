#!/usr/bin/env python3
"""
SSL Certificate Monitor and Renewal Tool
A real-world tool that every company needs but implements differently
Monitors SSL certificates and triggers renewal before expiration
"""

import ssl
import socket
import json
import os
import sys
import subprocess
import argparse
from datetime import datetime, timedelta
from urllib.parse import urlparse

class SSLCertMonitor:
    def __init__(self, config_file='/etc/ssl-monitor/config.json'):
        self.config = self.load_config(config_file)
        
    def load_config(self, config_file):
        """Load configuration from file or use defaults"""
        default_config = {
            "domains": [
                "api.mycompany.com",
                "app.mycompany.com",
                "www.mycompany.com"
            ],
            "warning_days": 30,
            "critical_days": 7,
            "slack_webhook": os.environ.get('SLACK_WEBHOOK_URL', ''),
            "email_alerts": os.environ.get('ALERT_EMAIL', ''),
            "auto_renew": False,
            "certbot_email": os.environ.get('CERTBOT_EMAIL', ''),
            "log_file": "/var/log/ssl-monitor.log"
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config file {config_file}: {e}")
        
        return default_config
    
    def get_cert_info(self, domain, port=443):
        """Get SSL certificate information for a domain"""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Parse expiration date
                    not_after = cert['notAfter']
                    expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                    
                    # Calculate days until expiration
                    days_until_expiry = (expiry_date - datetime.now()).days
                    
                    return {
                        'domain': domain,
                        'issuer': dict(x[0] for x in cert['issuer']),
                        'subject': dict(x[0] for x in cert['subject']),
                        'expiry_date': expiry_date.isoformat(),
                        'days_until_expiry': days_until_expiry,
                        'status': 'valid',
                        'san_domains': cert.get('subjectAltName', [])
                    }
                    
        except Exception as e:
            return {
                'domain': domain,
                'error': str(e),
                'status': 'error',
                'days_until_expiry': -1
            }
    
    def check_all_certificates(self):
        """Check all configured domains"""
        results = []
        
        for domain in self.config['domains']:
            print(f"Checking certificate for {domain}...")
            cert_info = self.get_cert_info(domain)
            results.append(cert_info)
        
        return results
    
    def analyze_results(self, results):
        """Analyze certificate results and determine actions needed"""
        alerts = []
        renewals_needed = []
        
        for cert in results:
            if cert['status'] == 'error':
                alerts.append({
                    'level': 'critical',
                    'domain': cert['domain'],
                    'message': f"Certificate check failed: {cert['error']}"
                })
                continue
            
            days_left = cert['days_until_expiry']
            domain = cert['domain']
            
            if days_left <= self.config['critical_days']:
                alerts.append({
                    'level': 'critical',
                    'domain': domain,
                    'message': f"Certificate expires in {days_left} days!"
                })
                renewals_needed.append(domain)
                
            elif days_left <= self.config['warning_days']:
                alerts.append({
                    'level': 'warning',
                    'domain': domain,
                    'message': f"Certificate expires in {days_left} days"
                })
        
        return alerts, renewals_needed
    
    def send_slack_alert(self, alerts):
        """Send alerts to Slack"""
        if not self.config['slack_webhook']:
            return
        
        try:
            import requests
            
            message = "SSL Certificate Alert:\n"
            for alert in alerts:
                emoji = "🔴" if alert['level'] == 'critical' else "🟡"
                message += f"{emoji} {alert['domain']}: {alert['message']}\n"
            
            payload = {
                "text": message,
                "username": "SSL Monitor",
                "icon_emoji": ":lock:"
            }
            
            response = requests.post(self.config['slack_webhook'], 
                                   json=payload, timeout=10)
            
            if response.status_code == 200:
                print("Slack alert sent successfully")
            else:
                print(f"Failed to send Slack alert: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending Slack alert: {e}")
    
    def renew_certificate(self, domain):
        """Attempt to renew certificate using certbot"""
        if not self.config['auto_renew']:
            print(f"Auto-renewal disabled for {domain}")
            return False
        
        try:
            print(f"Attempting to renew certificate for {domain}...")
            
            cmd = [
                'certbot', 'renew',
                '--domain', domain,
                '--non-interactive',
                '--agree-tos'
            ]
            
            if self.config['certbot_email']:
                cmd.extend(['--email', self.config['certbot_email']])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"Successfully renewed certificate for {domain}")
                
                # Reload nginx/apache if needed
                self.reload_web_server()
                return True
            else:
                print(f"Failed to renew certificate for {domain}: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error renewing certificate for {domain}: {e}")
            return False
    
    def reload_web_server(self):
        """Reload web server to pick up new certificates"""
        try:
            # Try nginx first
            result = subprocess.run(['nginx', '-t'], capture_output=True)
            if result.returncode == 0:
                subprocess.run(['systemctl', 'reload', 'nginx'])
                print("Reloaded nginx")
                return
            
            # Try apache
            result = subprocess.run(['apache2ctl', 'configtest'], capture_output=True)
            if result.returncode == 0:
                subprocess.run(['systemctl', 'reload', 'apache2'])
                print("Reloaded apache2")
                return
                
        except Exception as e:
            print(f"Warning: Could not reload web server: {e}")
    
    def log_results(self, results, alerts):
        """Log results to file"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'hostname': socket.gethostname(),
            'results': results,
            'alerts': alerts
        }
        
        try:
            os.makedirs(os.path.dirname(self.config['log_file']), exist_ok=True)
            with open(self.config['log_file'], 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")

def main():
    parser = argparse.ArgumentParser(description='SSL Certificate Monitor')
    parser.add_argument('--config', default='/etc/ssl-monitor/config.json',
                       help='Configuration file path')
    parser.add_argument('--check-domain', help='Check specific domain only')
    parser.add_argument('--renew', action='store_true',
                       help='Attempt to renew expiring certificates')
    parser.add_argument('--output', choices=['json', 'human'], default='human',
                       help='Output format')
    
    args = parser.parse_args()
    
    monitor = SSLCertMonitor(args.config)
    
    # Check specific domain or all domains
    if args.check_domain:
        results = [monitor.get_cert_info(args.check_domain)]
    else:
        results = monitor.check_all_certificates()
    
    # Analyze results
    alerts, renewals_needed = monitor.analyze_results(results)
    
    # Output results
    if args.output == 'json':
        output = {
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'alerts': alerts,
            'renewals_needed': renewals_needed
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nSSL Certificate Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        for cert in results:
            if cert['status'] == 'error':
                print(f"❌ {cert['domain']}: ERROR - {cert['error']}")
            else:
                days = cert['days_until_expiry']
                if days <= 7:
                    status = "❌ CRITICAL"
                elif days <= 30:
                    status = "⚠️  WARNING"
                else:
                    status = "✅ OK"
                
                print(f"{status} {cert['domain']}: {days} days until expiry")
        
        if alerts:
            print(f"\nAlerts ({len(alerts)}):")
            for alert in alerts:
                level_icon = "❌" if alert['level'] == 'critical' else "⚠️"
                print(f"  {level_icon} {alert['domain']}: {alert['message']}")
    
    # Send alerts if any
    if alerts:
        monitor.send_slack_alert(alerts)
    
    # Attempt renewals if requested
    if args.renew and renewals_needed:
        for domain in renewals_needed:
            monitor.renew_certificate(domain)
    
    # Log results
    monitor.log_results(results, alerts)
    
    # Exit with error code if critical alerts
    critical_alerts = [a for a in alerts if a['level'] == 'critical']
    return 1 if critical_alerts else 0

if __name__ == '__main__':
    sys.exit(main())
