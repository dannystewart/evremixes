# EvRemixes Analytics

This document explains the analytics features built into EvRemixes to help track download usage and understand user behavior.

## Overview

EvRemixes now includes built-in analytics to help you understand:

- How many people are downloading your remixes
- Which audio formats are most popular (FLAC vs ALAC)
- Which versions are preferred (Original vs Instrumental vs Both)
- Platform distribution (macOS, Windows, Linux)
- Download success rates

## How It Works

### 1. HTTP Headers Analytics

Every download request includes custom headers that your web server can log:

```http
X-Analytics-Session: <unique-session-id>
X-Analytics-User: <anonymous-user-hash>
X-Analytics-Track: <track-name>
X-Analytics-Format: <flac|m4a>
X-Analytics-Version: <original|instrumental|both>
X-Analytics-Platform: <Darwin|Windows|Linux>
X-Analytics-Python: <python-version>
```

### 2. Local Analytics Storage

Download sessions are automatically saved locally to `~/.evremixes/analytics.json` for users to view their own usage patterns.

### 3. Analytics Viewer

Users can view their download statistics using the `evremixes-stats` command.

## Server-Side Setup

To collect analytics on your web server, configure your web server to log the custom headers:

### Apache

Add to your virtual host configuration:

```apache
LogFormat "%h %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\" \"%{X-Analytics-Session}i\" \"%{X-Analytics-User}i\" \"%{X-Analytics-Track}i\" \"%{X-Analytics-Format}i\" \"%{X-Analytics-Version}i\" \"%{X-Analytics-Platform}i\"" evremixes
CustomLog logs/evremixes_analytics.log evremixes
```

### Nginx

Add to your server block:

```nginx
log_format evremixes '$remote_addr - $remote_user [$time_local] "$request" '
                     '$status $body_bytes_sent "$http_referer" "$http_user_agent" '
                     '"$http_x_analytics_session" "$http_x_analytics_user" '
                     '"$http_x_analytics_track" "$http_x_analytics_format" '
                     '"$http_x_analytics_version" "$http_x_analytics_platform"';

access_log /var/log/nginx/evremixes_analytics.log evremixes;
```

## Analytics Data Processing

You can process the server logs to generate insights:

### Basic Log Analysis

```bash
# Count total downloads
grep "X-Analytics-Track" /var/log/nginx/evremixes_analytics.log | wc -l

# Count unique users (by hash)
grep "X-Analytics-User" /var/log/nginx/evremixes_analytics.log | \
  awk '{print $10}' | sort | uniq | wc -l

# Format preferences
grep "X-Analytics-Format" /var/log/nginx/evremixes_analytics.log | \
  awk '{print $11}' | sort | uniq -c
```

### Advanced Analytics with Python

```python
import re
from collections import Counter

def parse_analytics_log(log_file):
    downloads = []
    with open(log_file) as f:
        for line in f:
            if 'X-Analytics-Track' in line:
                # Parse the log line and extract analytics data
                # Implementation depends on your log format
                pass
    return downloads

# Generate reports
downloads = parse_analytics_log('/var/log/nginx/evremixes_analytics.log')
format_stats = Counter(d['format'] for d in downloads)
platform_stats = Counter(d['platform'] for d in downloads)
```

## Privacy Considerations

The analytics system is designed with privacy in mind:

- **Anonymous User IDs**: User identifiers are SHA256 hashes of system information, not personally identifiable
- **No Personal Data**: No personal information, IP addresses, or file paths are collected
- **Local Storage**: User analytics are stored locally on their machine
- **Opt-out Friendly**: Easy to disable by modifying the code if needed

## Viewing Analytics

### For Users

Users can view their personal download statistics:

```bash
evremixes-stats
```

### For Developers

Process server logs to understand overall usage patterns and make data-driven decisions about:

- Which formats to prioritize
- Server capacity planning
- Feature development priorities

## Future Enhancements

Potential future analytics features:

- Real-time dashboard
- Geographic distribution (if IP geolocation is added)
- Download completion rates
- Peak usage times
- Integration with web analytics platforms

## Disabling Analytics

If you want to disable analytics entirely, you can modify the `TrackDownloader` class to skip adding the analytics headers, or set the headers to empty dictionaries.
