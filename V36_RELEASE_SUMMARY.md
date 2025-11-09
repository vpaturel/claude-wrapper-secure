# v36 Release Summary - Complete File Watcher

## Version
**v36-complete** (November 9, 2025)

## New Features

### 1. Simplified Thinking Parameter
- **Before**: `thinking: ThinkingConfig` (object with budget/model)
- **After**: `thinking: bool` (simple on/off)
- Implementation: Uses Claude CLI's `alwaysThinkingEnabled: true` in settings
- Usage: `{"thinking": true}` → Enable Extended Thinking mode

### 2. Automatic File Inclusion (Dual Mode)

#### Non-Streaming Mode (Snapshot)
- Parameter: `include_files: bool = False`
- Behavior: Reads all workspace files at end of request
- Returns: Complete file list with content in response
- Format:
```json
{
  "content": [...],
  "files": [
    {
      "path": "hello.txt",
      "content": "Hello World",
      "encoding": "text",
      "size": 11
    }
  ],
  "files_summary": {
    "total": 1,
    "total_size": 11
  }
}
```

#### Streaming Mode (Real-Time File Watcher)
- Parameter: `include_files: bool = False` + `stream: true`
- Behavior: Real-time file event monitoring during execution
- Returns: SSE events for files as they're created/modified
- Event Types:
  - `file_created` - Single file created
  - `file_modified` - Single file modified
  - `files_batch` - Multiple files (grouped)

#### Production File Watcher Features
Complete implementation with 6 problem fixes:

1. **Debouncing + Hashing** (Eliminate duplicates)
   - 0.5s debounce delay
   - SHA256 content hashing
   - Only send on real content changes

2. **Smart Filtering** (Ignore temporaries)
   - pathspec gitignore-like patterns
   - Ignores: .git/, __pycache__/, *.pyc, node_modules/, .env, etc.

3. **Retry + Stability** (Reliable reads)
   - Exponential backoff (3 retries)
   - File size stability check (2s timeout)
   - Handles permission errors gracefully

4. **Ordered Queue** (Guaranteed order)
   - Timestamp-based ordering
   - 0.5s ordering stability delay
   - Events sorted before sending

5. **Rate Limiting + Batching** (Handle bursts)
   - Token bucket algorithm (10 events/sec, burst 20)
   - Batch size: 5 files
   - Batch timeout: 1.0s
   - Prevents CPU/network spikes

6. **Context Manager Cleanup** (No leaks)
   - Guaranteed cleanup in `finally` block
   - Stops watcher even on errors
   - Logs stats (duration, files processed)

### 3. File Encoding Support
- **Text files**: UTF-8 encoding, returned as-is
- **Binary files**: Base64 encoding (images, PDFs, etc.)
- Encoding field in response: `"encoding": "text"` or `"encoding": "base64"`
- Max file size: 10 MB (configurable)

## Technical Implementation

### Files Modified
1. `server.py` (line 31)
   - Removed ThinkingConfig class
   - Changed thinking to Optional[bool]
   - Added include_files parameter
   - Version bumped to "v36-files-watcher"

2. `claude_oauth_api_secure_multitenant.py` (lines 654-895, 1108-1209)
   - Updated all 3 method signatures (thinking, include_files)
   - Snapshot mode: Uses get_workspace_snapshot()
   - Streaming mode: Integrated ProductionFileWatcher
   - Real-time file events interleaved with Claude SSE events

3. `file_watcher.py` (NEW - 432 lines)
   - ProductionFileWatcher class (all 6 fixes)
   - TokenBucketRateLimiter class
   - BatchProcessor class
   - get_workspace_snapshot() function
   - watch_workspace_production() context manager

4. `requirements.txt`
   - Added watchdog==3.0.0
   - Added pathspec==0.12.1

5. `V36_API_DOCUMENTATION.md` (NEW)
   - Complete API documentation
   - Examples (Python, JavaScript)
   - Use cases and anti-patterns
   - Performance and security considerations

## Use Cases

### ✅ Good Use Cases
- **Code Generation**: Get generated files automatically
  ```python
  response = api.create_message(
      messages=[{"role": "user", "content": "Create a FastAPI app"}],
      include_files=True
  )
  # Get files['main.py'], files['requirements.txt']
  ```

- **Real-Time Monitoring** (Streaming):
  ```python
  for event in api.create_message_streaming(
      messages=[{"role": "user", "content": "Generate 10 files"}],
      include_files=True,
      stream=True
  ):
      if event['type'] == 'file_created':
          save_file(event['path'], event['content'])
  ```

### ❌ Anti-Patterns
- Large repos: Don't use snapshot mode on repos with >100 files
- Binary-heavy: Avoid with many images/PDFs (Base64 overhead)
- Security: Don't use on sensitive workspaces

## Performance Impact

### Non-Streaming (Snapshot)
- **Overhead**: ~50-200ms (depends on file count)
- **Network**: +file sizes to response
- **Memory**: Loads all files in memory

### Streaming (File Watcher)
- **Overhead**: ~10-30ms setup (watchdog observer)
- **Network**: Real-time events as files created
- **Memory**: Minimal (only pending events)
- **CPU**: Token bucket limits to 10 events/sec

## Security

### Workspace Isolation
- Files ONLY from user's isolated workspace
- No access to other users' files
- No access to system files

### Ignored Patterns
Automatically filtered:
```
.git/, __pycache__/, *.pyc, *.swp, *~
node_modules/, .DS_Store, .claude/
*.tmp, *.temp, .env, .env.*
```

### File Size Limits
- Max file size: 10 MB
- Larger files: Logged warning, skipped

## Migration Guide

### From v35 to v36

#### Thinking Parameter
```python
# v35 (DEPRECATED)
thinking = {"budget_tokens": 10000, "type": "enabled"}

# v36 (NEW)
thinking = True  # Simple boolean
```

#### File Retrieval
```python
# v35 (Manual retrieval needed)
response = api.create_message(...)
# Need separate API call to get files

# v36 (Automatic)
response = api.create_message(..., include_files=True)
files = response['files']
```

## Breaking Changes
None - fully backward compatible:
- `thinking` parameter: Accepts both bool and dict (dict ignored)
- `include_files` parameter: Optional, defaults to False

## Next Steps
1. Deploy v36-complete to Cloud Run
2. Update client libraries
3. Update API documentation
4. Add metrics (file count, batch size)

## Deployment
```bash
# Build
gcloud builds submit --tag eu.gcr.io/claude-476509/claude-wrapper-secure:v36-complete

# Deploy
gcloud run deploy claude-wrapper-secure \
  --image eu.gcr.io/claude-476509/claude-wrapper-secure:v36-complete \
  --region europe-west1 \
  --project claude-476509

# Test
curl -X POST https://wrapper.claude.serenity-system.fr/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"oauth_credentials": {...}, "messages": [...], "include_files": true}'
```

## Changelog

### v36-complete (2025-11-09)
- feat: Simplified thinking parameter to boolean
- feat: Added automatic file inclusion (snapshot mode)
- feat: Added real-time file watcher (streaming mode)
- feat: Production file watcher with 6 problem fixes
- feat: Binary file support via Base64 encoding
- feat: Smart filtering (gitignore-like patterns)
- feat: Rate limiting and batching
- docs: Complete API documentation
- deps: Added watchdog==3.0.0, pathspec==0.12.1

### v35-thinking-fix (2025-11-09)
- fix: Correct thinking parameter format (alwaysThinkingEnabled)
- feat: Added fallback_model parameter

### v34-proactive (2025-11-08)
- feat: Proactive mode (automatic exhaustive responses)
