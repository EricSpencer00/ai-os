"""
Screen Context Manager
Maintains a rotating database of incremental screenshots for AI context awareness
"""
import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

class ScreenContextDB:
    """SQLite-based rotating screenshot database"""
    
    def __init__(self, db_path: str = "/tmp/auraos_screen_context.db", max_entries: int = 100):
        self.db_path = db_path
        self.max_entries = max_entries
        self.conn = None
        self.init_db()
    
    def init_db(self):
        """Initialize or connect to SQLite database"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()
        
        # Create table for screenshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                screenshot_hash TEXT UNIQUE,
                description TEXT,
                file_path TEXT,
                metadata JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create table for screen state changes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT,
                change_description TEXT,
                screenshot_id INTEGER REFERENCES screenshots(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
    
    def add_screenshot(self, file_path: str, description: str = "", metadata: Optional[Dict] = None) -> bool:
        """Add a screenshot to the database with deduplication"""
        if not os.path.exists(file_path):
            logging.warning(f"Screenshot file not found: {file_path}")
            return False
        
        # Calculate hash to detect duplicates
        file_hash = self._hash_file(file_path)
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO screenshots (timestamp, screenshot_hash, description, file_path, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                file_hash,
                description,
                file_path,
                json.dumps(metadata or {})
            ))
            self.conn.commit()
            self._prune_old_entries()
            logging.info(f"Added screenshot: {file_path}")
            return True
        except sqlite3.IntegrityError:
            # Duplicate screenshot, update timestamp
            logging.debug(f"Duplicate screenshot (same hash): {file_path}")
            return False
    
    def add_state_change(self, event_type: str, change_description: str, screenshot_id: Optional[int] = None):
        """Record a state change event"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO state_changes (timestamp, event_type, change_description, screenshot_id)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            event_type,
            change_description,
            screenshot_id
        ))
        self.conn.commit()
        logging.info(f"Recorded state change: {event_type} - {change_description}")
    
    def get_recent_context(self, minutes: int = 5) -> Dict:
        """Get recent screenshots and state changes for AI context"""
        cursor = self.conn.cursor()
        cutoff_time = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        
        # Get recent screenshots
        cursor.execute("""
            SELECT id, timestamp, description, file_path, metadata
            FROM screenshots
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """, (cutoff_time,))
        
        screenshots = []
        for row in cursor.fetchall():
            screenshots.append({
                'id': row[0],
                'timestamp': row[1],
                'description': row[2],
                'file_path': row[3],
                'metadata': json.loads(row[4] or '{}')
            })
        
        # Get recent state changes
        cursor.execute("""
            SELECT timestamp, event_type, change_description, screenshot_id
            FROM state_changes
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """, (cutoff_time,))
        
        changes = []
        for row in cursor.fetchall():
            changes.append({
                'timestamp': row[0],
                'event_type': row[1],
                'description': row[2],
                'screenshot_id': row[3]
            })
        
        return {
            'screenshots': screenshots,
            'state_changes': changes,
            'context_window': f"Last {minutes} minutes"
        }
    
    def get_last_screenshot(self) -> Optional[Dict]:
        """Get the most recent screenshot"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, description, file_path, metadata
            FROM screenshots
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'timestamp': row[1],
                'description': row[2],
                'file_path': row[3],
                'metadata': json.loads(row[4] or '{}')
            }
        return None
    
    def get_screenshot_by_id(self, screenshot_id: int) -> Optional[Dict]:
        """Get a specific screenshot by ID"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, description, file_path, metadata
            FROM screenshots
            WHERE id = ?
        """, (screenshot_id,))
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'timestamp': row[1],
                'description': row[2],
                'file_path': row[3],
                'metadata': json.loads(row[4] or '{}')
            }
        return None
    
    def _hash_file(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _prune_old_entries(self):
        """Remove oldest entries if max_entries exceeded"""
        cursor = self.conn.cursor()
        cursor.execute(f"""
            DELETE FROM screenshots WHERE id IN (
                SELECT id FROM screenshots
                ORDER BY created_at ASC
                LIMIT MAX(0, (SELECT COUNT(*) FROM screenshots) - ?)
            )
        """, (self.max_entries,))
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        self.close()


class ScreenCaptureManager:
    """Manages incremental screen capture with change detection"""
    
    def __init__(self, output_dir: str = "/tmp/auraos_screenshots"):
        self.output_dir = output_dir
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self.db = ScreenContextDB()
        self.last_screenshot_hash = None
    
    def capture_screenshot(self, description: str = "") -> Optional[str]:
        """Capture screenshot and store in DB if changed"""
        import subprocess
        import hashlib
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        screenshot_file = os.path.join(self.output_dir, f"screen_{timestamp}.png")
        
        try:
            # Use screencapture on macOS or scrot on Linux
            if os.path.exists('/usr/sbin/screencapture'):
                subprocess.run(['/usr/sbin/screencapture', '-x', screenshot_file], check=True)
            else:
                # Try scrot (Linux)
                subprocess.run(['scrot', screenshot_file], check=True)
            
            # Check if this is different from last screenshot
            file_hash = self._hash_file(screenshot_file)
            if file_hash != self.last_screenshot_hash:
                self.last_screenshot_hash = file_hash
                
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'description': description
                }
                
                self.db.add_screenshot(screenshot_file, description, metadata)
                logging.info(f"Captured new screenshot: {screenshot_file}")
                return screenshot_file
            else:
                # Same as last, clean up
                os.remove(screenshot_file)
                return None
                
        except Exception as e:
            logging.error(f"Failed to capture screenshot: {e}")
            return None
    
    def _hash_file(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def get_context_for_ai(self, minutes: int = 5) -> Dict:
        """Get recent screen history for AI context"""
        context = self.db.get_recent_context(minutes)
        
        # Add file contents for processing
        for screenshot in context['screenshots']:
            if os.path.exists(screenshot['file_path']):
                screenshot['file_exists'] = True
                # OCR could be integrated here if needed
            else:
                screenshot['file_exists'] = False
        
        return context
    
    def close(self):
        """Clean up resources"""
        self.db.close()
