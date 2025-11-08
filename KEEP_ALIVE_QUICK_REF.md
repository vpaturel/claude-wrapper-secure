# Keep-Alive Quick Reference

**Status**: ✅ WORKING (2025-11-06)

## The Discovery

**Previous belief**: Keep-alive impossible (EOF required)
**Reality**: `--input-format stream-json` processes messages WITHOUT EOF!

## Working Code

```python
from streaming_bidirectional_v2 import BidirectionalStreamingClient, StreamingConfig

config = StreamingConfig(model="haiku")

with BidirectionalStreamingClient(config) as client:
    # Message 1
    for event in client.send_message("Question 1"):
        if event.get("type") == "assistant":
            message = event.get("message", {})
            for block in message.get("content", []):
                if block.get("type") == "text":
                    print(block["text"], end="")

    # Wait 5 seconds (process stays alive!)
    time.sleep(5)

    # Message 2 - SAME process!
    for event in client.send_message("Question 2"):
        # Extract text...
        pass
```

## Test Results

```
✅ 3 messages handled by same process (PID: 947137)
✅ 10 seconds total idle time
✅ All responses correct: OK1, OK2, OK3
✅ 2.1× faster than spawning new processes
```

## Key Flags

```bash
claude \
  --input-format stream-json \    # ← Process messages line-by-line
  --output-format stream-json \   # ← Output JSON events
  --print                         # ← No interactive prompts
```

## Event Format

**Input** (send to stdin):
```json
{"type": "user", "message": {"role": "user", "content": "Your question"}}
```

**Output** (read from stdout):
```json
{"type": "assistant", "message": {"content": [{"type": "text", "text": "Response"}]}}
{"type": "result", "result": "Full response", "usage": {...}}
```

## Architecture

- **Thread-based reader**: Non-blocking stdout consumption
- **Queue**: Thread-safe event passing
- **No wait()**: stdin stays open between messages
- **Context manager**: Automatic cleanup

## Files

- **Implementation**: `streaming_bidirectional_v2.py`
- **Full docs**: `KEEP_ALIVE_SUCCESS.md`
- **Test**: `/tmp/test_v2_keepalive.py`

## Next Steps

1. ⏳ Integrate into `claude_oauth_api_secure_multitenant.py`
2. ⏳ Add process pooling (one process per user)
3. ⏳ Deploy to Cloud Run
