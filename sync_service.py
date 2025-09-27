#!/usr/bin/env python3
"""
Simple Sync Service for Cin7 Stock Forecasting
Maintains database synchronization with Cin7 API
"""

import os
import sys
import sqlite3
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz
from dotenv import load_dotenv

# Import our existing Cin7 client
from unified_stock_app import UnifiedCin7Client

# Load environment variables
load_dotenv()

class SyncService:
    def __init__(self):
        self.db_path = self._get_db_path()
        self.lock_file = 'sync.lock'
        self.setup_logging()
        self.cin7_client = None
        
        # Configuration from environment
        self.sync_enabled = os.getenv('SYNC_ENABLED', 'true').lower() == 'true'
        self.overlap_hours = int(os.getenv('SYNC_OVERLAP_HOURS', '1'))
        self.max_orders_per_batch = int(os.getenv('SYNC_MAX_ORDERS_PER_BATCH', '1000'))
        self.timeout_minutes = int(os.getenv('SYNC_TIMEOUT_MINUTES', '45'))
        
        # Initialize database
        self._init_database()
    
    def _get_db_path(self) -> str:
        """Get database path (same logic as main app)"""
        db_path = os.environ.get('DATABASE_PATH', 'stock_forecast.db')
        
        # Check for Render persistent disk
        if db_path == 'stock_forecast.db' and os.path.exists('/data/db'):
            db_path = '/data/db/stock_forecast.db'
        
        return db_path
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_format = '%(asctime)s [%(levelname)s] %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('sync_service.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self):
        """Initialize database with sync tables if they don't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Read and execute migration SQL
            with open('database_migrations.sql', 'r') as f:
                migration_sql = f.read()
            
            # Execute each statement separately
            for statement in migration_sql.split(';'):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            
            conn.commit()
            conn.close()
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    def get_last_sync_time(self) -> str:
        """Get the last successful sync timestamp"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT last_sync_timestamp FROM sync_state WHERE sync_type = 'hourly'"
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            else:
                # Default to June 11, 2025 if no record
                return '2025-06-11T00:00:00Z'
                
        except Exception as e:
            self.logger.error(f"Failed to get last sync time: {e}")
            return '2025-06-11T00:00:00Z'
    
    def update_last_sync_time(self, timestamp: str):
        """Update the last successful sync timestamp"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO sync_state (sync_type, last_sync_timestamp, last_sync_success, updated_at)
                VALUES ('hourly', ?, 1, CURRENT_TIMESTAMP)
            """, (timestamp,))
            
            conn.commit()
            conn.close()
            self.logger.info(f"Updated last sync time to: {timestamp}")
            
        except Exception as e:
            self.logger.error(f"Failed to update last sync time: {e}")
    
    def log_sync_start(self, sync_type: str, created_since: str) -> int:
        """Log the start of a sync operation, return log ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sync_log (sync_type, started_at, status, created_since_date)
                VALUES (?, CURRENT_TIMESTAMP, 'running', ?)
            """, (sync_type, created_since))
            
            log_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.info(f"Started {sync_type} sync (log_id: {log_id}) from {created_since}")
            return log_id
            
        except Exception as e:
            self.logger.error(f"Failed to log sync start: {e}")
            return 0
    
    def log_sync_complete(self, log_id: int, stats: Dict):
        """Log successful completion of sync operation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sync_log 
                SET completed_at = CURRENT_TIMESTAMP,
                    status = 'completed',
                    orders_processed = ?,
                    lines_stored = ?,
                    total_api_calls = ?
                WHERE id = ?
            """, (
                stats.get('orders_found', 0),
                stats.get('lines_stored', 0),
                stats.get('api_calls', 0),
                log_id
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Sync completed (log_id: {log_id}): {stats}")
            
        except Exception as e:
            self.logger.error(f"Failed to log sync completion: {e}")
    
    def log_sync_error(self, log_id: int, error: str):
        """Log sync operation failure"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sync_log 
                SET completed_at = CURRENT_TIMESTAMP,
                    status = 'failed',
                    error_message = ?
                WHERE id = ?
            """, (error, log_id))
            
            conn.commit()
            conn.close()
            
            self.logger.error(f"Sync failed (log_id: {log_id}): {error}")
            
        except Exception as e:
            self.logger.error(f"Failed to log sync error: {e}")
    
    def is_sync_running(self) -> bool:
        """Check if a sync is currently running"""
        if not os.path.exists(self.lock_file):
            return False
        
        try:
            with open(self.lock_file, 'r') as f:
                lock_data = json.load(f)
            
            # Check if lock is stale (older than timeout)
            lock_time = datetime.fromisoformat(lock_data['started_at'])
            now = datetime.now()
            
            if (now - lock_time).total_seconds() > (self.timeout_minutes * 60):
                self.logger.warning("Removing stale lock file")
                os.remove(self.lock_file)
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Invalid lock file, removing: {e}")
            try:
                os.remove(self.lock_file)
            except:
                pass
            return False
    
    def create_lock_file(self) -> bool:
        """Create lock file to prevent concurrent syncs"""
        if self.is_sync_running():
            return False
        
        try:
            lock_data = {
                'pid': os.getpid(),
                'started_at': datetime.now().isoformat(),
                'timeout_minutes': self.timeout_minutes
            }
            
            with open(self.lock_file, 'w') as f:
                json.dump(lock_data, f, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create lock file: {e}")
            return False
    
    def remove_lock_file(self):
        """Remove lock file after sync completion"""
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except Exception as e:
            self.logger.warning(f"Failed to remove lock file: {e}")
    
    def hourly_sync(self) -> Dict:
        """Perform hourly sync operation"""
        if not self.sync_enabled:
            return {'success': False, 'error': 'Sync disabled in configuration'}
        
        # Check if sync is already running
        if not self.create_lock_file():
            error_msg = "Sync already running or failed to create lock"
            self.logger.warning(error_msg)
            return {'success': False, 'error': error_msg}
        
        log_id = 0
        try:
            # Initialize Cin7 client
            self.cin7_client = UnifiedCin7Client()
            
            # Get last sync time and calculate overlap
            last_sync = self.get_last_sync_time()
            last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            
            # Sync from overlap_hours before last sync for safety
            sync_from_dt = last_sync_dt - timedelta(hours=self.overlap_hours)
            created_since = sync_from_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Log sync start
            log_id = self.log_sync_start('hourly', created_since)
            
            self.logger.info(f"Starting hourly sync from: {created_since}")
            
            # Use existing sync method from UnifiedCin7Client
            result = self.cin7_client.sync_recent_orders(
                created_since=created_since,
                max_orders=self.max_orders_per_batch
            )
            
            if result.get('success'):
                # Update last sync time to now
                now_utc = datetime.now(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
                self.update_last_sync_time(now_utc)
                
                # Log successful completion
                stats = {
                    'orders_found': result.get('orders_found', 0),
                    'lines_stored': result.get('lines_stored', 0),
                    'skipped_existing': result.get('skipped_existing', 0),
                    'api_calls': result.get('orders_found', 0) + 1  # Estimate
                }
                
                self.log_sync_complete(log_id, stats)
                
                self.logger.info(f"Hourly sync completed successfully: {stats}")
                
                return {
                    'success': True,
                    'message': 'Hourly sync completed',
                    'stats': stats,
                    'created_since': created_since
                }
            else:
                error_msg = result.get('error', 'Unknown sync error')
                self.log_sync_error(log_id, error_msg)
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"Hourly sync failed: {str(e)}"
            self.logger.error(error_msg)
            if log_id:
                self.log_sync_error(log_id, error_msg)
            return {'success': False, 'error': error_msg}
        
        finally:
            self.remove_lock_file()
    
    def get_sync_status(self) -> Dict:
        """Get current sync service status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get last sync info
            cursor.execute("""
                SELECT sync_type, started_at, completed_at, status, 
                       orders_processed, lines_stored, error_message
                FROM sync_log 
                ORDER BY started_at DESC 
                LIMIT 1
            """)
            
            last_sync = cursor.fetchone()
            
            # Get running sync if any
            cursor.execute("""
                SELECT COUNT(*) FROM sync_log 
                WHERE status = 'running'
            """)
            
            running_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'is_running': self.is_sync_running(),
                'sync_enabled': self.sync_enabled,
                'running_syncs': running_count,
                'last_sync': {
                    'type': last_sync[0] if last_sync else None,
                    'started_at': last_sync[1] if last_sync else None,
                    'completed_at': last_sync[2] if last_sync else None,
                    'status': last_sync[3] if last_sync else None,
                    'orders_processed': last_sync[4] if last_sync else 0,
                    'lines_stored': last_sync[5] if last_sync else 0,
                    'error_message': last_sync[6] if last_sync else None
                } if last_sync else None,
                'last_sync_time': self.get_last_sync_time()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get sync status: {e}")
            return {
                'is_running': False,
                'sync_enabled': self.sync_enabled,
                'error': str(e)
            }


def main():
    """Main entry point for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python sync_service.py <command>")
        print("Commands:")
        print("  hourly    - Run hourly sync")
        print("  status    - Show sync status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    service = SyncService()
    
    if command == 'hourly':
        result = service.hourly_sync()
        if result['success']:
            print(f"✅ {result['message']}")
            if 'stats' in result:
                stats = result['stats']
                print(f"📊 Orders: {stats['orders_found']}, Lines: {stats['lines_stored']}, Skipped: {stats['skipped_existing']}")
        else:
            print(f"❌ Sync failed: {result['error']}")
            sys.exit(1)
    
    elif command == 'status':
        status = service.get_sync_status()
        print(f"🔄 Sync Service Status:")
        print(f"  Enabled: {status['sync_enabled']}")
        print(f"  Running: {status['is_running']}")
        print(f"  Last sync: {status['last_sync_time']}")
        if status.get('last_sync'):
            last = status['last_sync']
            print(f"  Last operation: {last['type']} - {last['status']}")
            if last['completed_at']:
                print(f"  Completed: {last['completed_at']}")
                print(f"  Results: {last['orders_processed']} orders, {last['lines_stored']} lines")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
