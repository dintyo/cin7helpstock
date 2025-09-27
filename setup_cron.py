#!/usr/bin/env python3
"""
Cron Job Setup Helper for Sync Service
Helps configure automatic hourly sync on different platforms
"""

import os
import sys
import subprocess
from pathlib import Path

def get_app_path():
    """Get the full path to the application directory"""
    return os.path.abspath(os.path.dirname(__file__))

def create_cron_entry(interval_minutes=60):
    """Create cron job entry for sync service"""
    app_path = get_app_path()
    python_path = sys.executable
    
    # Cron job command
    if interval_minutes == 60:
        cron_schedule = "0 * * * *"  # Every hour
        comment = "Hourly sync"
    elif interval_minutes == 30:
        cron_schedule = "0,30 * * * *"  # Every 30 minutes
        comment = "Every 30 minutes sync"
    elif interval_minutes == 15:
        cron_schedule = "*/15 * * * *"  # Every 15 minutes
        comment = "Every 15 minutes sync (development)"
    else:
        cron_schedule = f"*/{interval_minutes} * * * *"
        comment = f"Every {interval_minutes} minutes sync"
    
    cron_command = f'cd {app_path} && {python_path} sync_service.py hourly'
    log_file = os.path.join(app_path, 'sync_service.log')
    
    cron_entry = f"{cron_schedule} {cron_command} >> {log_file} 2>&1"
    
    return {
        'schedule': cron_schedule,
        'command': cron_command,
        'full_entry': cron_entry,
        'comment': comment,
        'log_file': log_file
    }

def show_cron_instructions():
    """Show instructions for setting up cron job"""
    print("🔧 Cron Job Setup Instructions")
    print("=" * 50)
    
    # Production setup (hourly)
    prod_entry = create_cron_entry(60)
    print(f"\n📅 PRODUCTION SETUP (Hourly Sync):")
    print(f"1. Open crontab: crontab -e")
    print(f"2. Add this line:")
    print(f"   {prod_entry['full_entry']}")
    
    # Development setup (15 minutes)
    dev_entry = create_cron_entry(15)
    print(f"\n🧪 DEVELOPMENT SETUP (15-minute sync for testing):")
    print(f"1. Open crontab: crontab -e")
    print(f"2. Add this line:")
    print(f"   {dev_entry['full_entry']}")
    
    print(f"\n📋 Manual Commands:")
    print(f"• Test sync: python sync_service.py hourly")
    print(f"• Check status: python sync_service.py status")
    print(f"• View logs: tail -f {prod_entry['log_file']}")
    
    print(f"\n⚠️  Important Notes:")
    print(f"• Make sure your .env file has SYNC_ENABLED=true")
    print(f"• Test the sync manually first before setting up cron")
    print(f"• Logs will be written to: {prod_entry['log_file']}")
    print(f"• The sync service will prevent overlapping runs automatically")

def create_systemd_service():
    """Create systemd service file (for Linux servers)"""
    app_path = get_app_path()
    python_path = sys.executable
    
    service_content = f"""[Unit]
Description=Cin7 Stock Sync Service
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'www-data')}
WorkingDirectory={app_path}
Environment=PATH={os.path.dirname(python_path)}
ExecStart={python_path} sync_service.py hourly
Restart=no
StandardOutput=append:{app_path}/sync_service.log
StandardError=append:{app_path}/sync_service.log

[Install]
WantedBy=multi-user.target
"""
    
    service_file = 'cin7-sync.service'
    
    with open(service_file, 'w') as f:
        f.write(service_content)
    
    print(f"\n🐧 SYSTEMD SERVICE CREATED: {service_file}")
    print(f"To install:")
    print(f"1. sudo cp {service_file} /etc/systemd/system/")
    print(f"2. sudo systemctl daemon-reload")
    print(f"3. sudo systemctl enable cin7-sync.timer")
    print(f"4. sudo systemctl start cin7-sync.timer")
    
    # Also create timer file
    timer_content = """[Unit]
Description=Run Cin7 Stock Sync Service hourly
Requires=cin7-sync.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
"""
    
    timer_file = 'cin7-sync.timer'
    with open(timer_file, 'w') as f:
        f.write(timer_content)
    
    print(f"\nTimer file created: {timer_file}")
    return service_file, timer_file

def create_windows_task():
    """Create Windows Task Scheduler setup instructions"""
    app_path = get_app_path()
    python_path = sys.executable
    
    print(f"\n🪟 WINDOWS TASK SCHEDULER SETUP:")
    print(f"1. Open Task Scheduler (taskschd.msc)")
    print(f"2. Create Basic Task...")
    print(f"3. Name: 'Cin7 Stock Sync'")
    print(f"4. Trigger: Daily")
    print(f"5. Repeat task every: 1 hour")
    print(f"6. Action: Start a program")
    print(f"7. Program: {python_path}")
    print(f"8. Arguments: sync_service.py hourly")
    print(f"9. Start in: {app_path}")
    print(f"\nOr use PowerShell command:")
    
    ps_command = f'''schtasks /create /tn "Cin7StockSync" /tr "'{python_path}' sync_service.py hourly" /sc hourly /st 00:00 /sd {app_path}'''
    print(f"{ps_command}")

def check_dependencies():
    """Check if all dependencies are available"""
    print("🔍 Checking Dependencies...")
    
    # Check Python modules
    required_modules = ['requests', 'flask', 'python-dotenv', 'pytz']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module.replace('-', '_'))
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - MISSING")
            missing_modules.append(module)
    
    # Check files
    required_files = ['unified_stock_app.py', 'database_migrations.sql', '.env']
    missing_files = []
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - MISSING")
            missing_files.append(file)
    
    if missing_modules:
        print(f"\n⚠️  Install missing modules:")
        print(f"pip install {' '.join(missing_modules)}")
    
    if missing_files:
        print(f"\n⚠️  Missing files: {', '.join(missing_files)}")
    
    return len(missing_modules) == 0 and len(missing_files) == 0

def main():
    """Main setup function"""
    if len(sys.argv) < 2:
        print("Usage: python setup_cron.py <command>")
        print("Commands:")
        print("  instructions  - Show cron setup instructions")
        print("  systemd      - Create systemd service files")
        print("  windows      - Show Windows Task Scheduler setup")
        print("  check        - Check dependencies")
        print("  test         - Test sync service")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'instructions':
        show_cron_instructions()
    
    elif command == 'systemd':
        create_systemd_service()
    
    elif command == 'windows':
        create_windows_task()
    
    elif command == 'check':
        if check_dependencies():
            print("\n✅ All dependencies satisfied!")
        else:
            print("\n❌ Please install missing dependencies before proceeding.")
            sys.exit(1)
    
    elif command == 'test':
        print("🧪 Testing sync service...")
        try:
            result = subprocess.run([sys.executable, 'sync_service.py', 'status'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Sync service is working!")
                print(result.stdout)
            else:
                print("❌ Sync service test failed:")
                print(result.stderr)
                sys.exit(1)
                
        except subprocess.TimeoutExpired:
            print("❌ Sync service test timed out")
            sys.exit(1)
        except FileNotFoundError:
            print("❌ sync_service.py not found")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()
