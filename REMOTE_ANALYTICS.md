# Remote Analytics Configuration

EvRemixes can optionally send analytics data to a remote server endpoint in addition to local storage.

## Configuration

To enable remote analytics, add the `analytics_endpoint` parameter to your EvRemixes configuration:

```python
from evremixes.config import DownloadConfig

config = DownloadConfig(
    # ... your existing config ...
    analytics_endpoint="https://your-server.com/api/evremixes/analytics"
)
```

## Data Sent

The following data is sent via POST request to your endpoint:

```json
{
    "session_id": "abc12345",
    "user_hash": "a1b2c3d4e5f6",
    "track_name": "Track Name",
    "format": "FLAC",
    "version": "Original",
    "platform": "Darwin",
    "python_version": "3.12",
    "success": true
}
```

## Server Requirements

Your endpoint should:

- Accept POST requests with JSON payload
- Return HTTP 200 for successful processing
- Handle the data structure shown above

## Privacy

- All data is anonymous (user_hash is SHA256 of machine info)
- No personal information or IP addresses are sent from client
- Server may log IP addresses for basic analytics
- Analytics failures never affect downloads

## Example Server Implementation

See the Flask implementation in the Prism bot platform for a complete example with:

- Database storage
- Analytics dashboard
- Charts and visualizations
- User authentication

## Disabling Remote Analytics

Simply omit the `analytics_endpoint` parameter or set it to `None` to disable remote analytics while keeping local analytics active.
