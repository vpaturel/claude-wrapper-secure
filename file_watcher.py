#!/usr/bin/env python3
"""
Production File Watcher with all fixes:
- Debouncing + hashing (fix duplicates)
- Filtering (fix temporaries)
- Retry + stability (fix timing)
- Ordered queue (fix order)
- Rate limiting + batching (fix bursts)
- Context manager cleanup (fix leaks)
"""

import hashlib
import time
import pathspec
from pathlib import Path
from queue import Queue, Empty
from contextlib import contextmanager
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from collections import deque
from typing import Optional, List, Dict
import logging
import base64

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """Token bucket algorithm for rate limiting"""

    def __init__(self, rate: int = 10, capacity: int = 20):
        """
        rate: tokens per second
        capacity: max burst size
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()

    def refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens"""
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class BatchProcessor:
    """Group multiple files into single response"""

    def __init__(self, batch_size: int = 5, batch_timeout: float = 1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.batch = []
        self.batch_start = None

    def add_file(self, file_data):
        if not self.batch:
            self.batch_start = time.time()

        self.batch.append(file_data)

    def should_flush(self) -> bool:
        """Check if batch should be sent"""
        if not self.batch:
            return False

        # Flush if batch full
        if len(self.batch) >= self.batch_size:
            return True

        # Flush if timeout
        if time.time() - self.batch_start > self.batch_timeout:
            return True

        return False

    def flush(self):
        """Send batch as single event"""
        if not self.batch:
            return None

        batch = self.batch.copy()
        self.batch = []
        self.batch_start = None

        return {
            "type": "files_batch",
            "files": batch,
            "count": len(batch)
        }


class ProductionFileWatcher(FileSystemEventHandler):
    """
    Production-ready file watcher with ALL fixes:
    - Debouncing + hashing (fix duplicates)
    - Filtering (fix temporaries)
    - Retry + stability (fix timing)
    - Ordered queue (fix order)
    - Rate limiting + batching (fix bursts)
    """

    IGNORE_PATTERNS = """
.git/
__pycache__/
*.pyc
*.swp
*~
node_modules/
.DS_Store
.claude/
*.tmp
*.temp
.env
.env.*
    """.strip().split('\n')

    def __init__(
        self,
        workspace: Path,
        event_queue: Queue,
        debounce_delay: float = 0.5,
        rate_limit: int = 10,
        batch_size: int = 5,
        max_file_size: int = 10 * 1024 * 1024
    ):
        self.workspace = workspace
        self.event_queue = event_queue
        self.debounce_delay = debounce_delay
        self.max_file_size = max_file_size

        # Filtering
        self.ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', self.IGNORE_PATTERNS)

        # Debouncing
        self.pending = {}  # {path: last_time}
        self.file_hashes = {}  # {path: hash}

        # Ordering
        self.ordered_events = []  # [(timestamp, event)]

        # Rate limiting
        self.rate_limiter = TokenBucketRateLimiter(rate=rate_limit)

        # Batching
        self.batcher = BatchProcessor(batch_size=batch_size)

        logger.info(f"📁 File watcher initialized for {workspace}")

    def should_ignore(self, path: str) -> bool:
        """Check if file should be ignored"""
        try:
            relative = Path(path).relative_to(self.workspace)
            return self.ignore_spec.match_file(str(relative))
        except:
            return True

    def on_created(self, event):
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self.pending[event.src_path] = time.time()
        logger.debug(f"➕ File created (pending): {event.src_path}")

    def on_modified(self, event):
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self.pending[event.src_path] = time.time()
        logger.debug(f"✏️  File modified (pending): {event.src_path}")

    def process_pending(self):
        """Process all pending events (debounced, hashed, ordered, rate-limited)"""
        now = time.time()

        # 1. Get stable files (debounced)
        stable_files = []
        for path, last_time in list(self.pending.items()):
            if now - last_time > self.debounce_delay:
                stable_files.append(path)
                del self.pending[path]

        # 2. Process each stable file
        for path in stable_files:
            file_path = Path(path)

            # Check size
            try:
                file_size = file_path.stat().st_size
                if file_size > self.max_file_size:
                    logger.warning(f"⚠️  File too large ({file_size} bytes): {path}")
                    continue
            except Exception as e:
                logger.debug(f"Cannot stat {path}: {e}")
                continue

            # Wait for stability
            if not self.wait_for_stable(file_path):
                logger.debug(f"File not stable, skipping: {path}")
                continue

            # Read with retry
            content, encoding = self.read_file_safe(file_path)
            if content is None:
                logger.warning(f"Cannot read {path}")
                continue

            # Hash to detect real changes
            current_hash = hashlib.sha256(content.encode() if isinstance(content, str) else content).hexdigest()
            if current_hash == self.file_hashes.get(path):
                logger.debug(f"No real change (same hash): {path}")
                continue  # No real change

            self.file_hashes[path] = current_hash

            # Add to ordered queue with timestamp
            self.ordered_events.append({
                "timestamp": time.time(),
                "type": "file_created",
                "path": str(file_path.relative_to(self.workspace)),
                "content": content,
                "encoding": encoding,
                "hash": current_hash,
                "size": file_size
            })

            logger.info(f"✅ File ready: {file_path.name} ({file_size} bytes, {encoding})")

        # 3. Process ordered events (respect rate limit)
        self.flush_events()

    def flush_events(self):
        """Flush ordered events with rate limiting and batching"""
        now = time.time()

        # Get events ready to send (>0.5s old for ordering stability)
        ready = [e for e in self.ordered_events if now - e["timestamp"] > 0.5]
        ready.sort(key=lambda e: e["timestamp"])

        # Remove from queue
        self.ordered_events = [e for e in self.ordered_events if now - e["timestamp"] <= 0.5]

        # Apply rate limiting + batching
        for event in ready:
            if self.rate_limiter.consume():
                # Add to batch
                self.batcher.add_file(event)

                # Flush batch if ready
                if self.batcher.should_flush():
                    batch = self.batcher.flush()
                    self.event_queue.put(batch)
                    logger.info(f"📦 Sent batch of {batch['count']} files")
            else:
                # Rate limit exceeded, re-queue
                self.ordered_events.append(event)

    def wait_for_stable(self, path: Path, timeout: float = 2.0) -> bool:
        """Wait until file size is stable"""
        last_size = None
        start = time.time()

        while time.time() - start < timeout:
            try:
                current_size = path.stat().st_size
                if last_size == current_size:
                    return True
                last_size = current_size
                time.sleep(0.05)
            except:
                return False
        return False

    def read_file_safe(self, path: Path, max_retries: int = 3) -> tuple[Optional[str], str]:
        """Read file with exponential backoff. Returns (content, encoding)"""
        for attempt in range(max_retries):
            try:
                # Try reading as text
                content = path.read_text(encoding='utf-8')
                return (content, "text")
            except UnicodeDecodeError:
                # Binary file, use base64
                try:
                    content = base64.b64encode(path.read_bytes()).decode('utf-8')
                    return (content, "base64")
                except Exception as e:
                    logger.error(f"Error reading binary {path}: {e}")
                    return (None, "unknown")
            except (PermissionError, OSError) as e:
                if attempt < max_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)
                    logger.debug(f"Retry {attempt+1}/{max_retries} for {path} (wait {wait_time}s)")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Cannot read {path} after {max_retries} attempts: {e}")
                    return (None, "error")

        return (None, "error")


@contextmanager
def watch_workspace_production(workspace: Path, event_queue: Queue):
    """Production context manager with guaranteed cleanup"""
    observer = Observer()
    handler = ProductionFileWatcher(workspace, event_queue)
    observer.schedule(handler, str(workspace), recursive=True)
    observer.start()

    start_time = time.time()
    max_duration = 600  # 10 minutes max

    try:
        yield handler

    finally:
        # Guaranteed cleanup
        logger.info("🛑 Stopping file watcher...")
        observer.stop()
        observer.join(timeout=5)

        # Log stats
        duration = time.time() - start_time
        logger.info(f"📊 Watcher stats: {duration:.1f}s, {len(handler.file_hashes)} files processed")


def get_workspace_snapshot(workspace: Path, max_file_size: int = 10 * 1024 * 1024) -> List[Dict]:
    """
    Simple snapshot approach (no file watcher).
    Returns all files in workspace at current time.
    """
    files = []
    ignore_patterns = ProductionFileWatcher.IGNORE_PATTERNS
    ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)

    for file_path in workspace.rglob("*"):
        # Skip directories
        if not file_path.is_file():
            continue

        # Skip ignored files
        try:
            relative = file_path.relative_to(workspace)
            if ignore_spec.match_file(str(relative)):
                continue
        except:
            continue

        # Skip large files
        try:
            file_size = file_path.stat().st_size
            if file_size > max_file_size:
                logger.warning(f"Skipping large file: {file_path.name} ({file_size} bytes)")
                continue
        except:
            continue

        # Read file
        try:
            content = file_path.read_text(encoding='utf-8')
            encoding = "text"
        except UnicodeDecodeError:
            content = base64.b64encode(file_path.read_bytes()).decode('utf-8')
            encoding = "base64"
        except Exception as e:
            logger.error(f"Cannot read {file_path}: {e}")
            continue

        files.append({
            "path": str(relative),
            "content": content,
            "encoding": encoding,
            "size": file_size
        })

    logger.info(f"📸 Workspace snapshot: {len(files)} files")
    return files
