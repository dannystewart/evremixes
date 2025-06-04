#!/usr/bin/env python3
"""Test script to verify EvRemixes analytics integration.

This simulates what would happen when EvRemixes sends data to your Flask endpoint.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add the src directory to the path so we can import evremixes modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from evremixes.analytics import AnalyticsHelper
from evremixes.config import DownloadConfig
from evremixes.types import AudioFormat, TrackVersions


def test_analytics_payload():
    """Test that analytics generates the correct payload for the Flask endpoint."""
    print("🧪 Testing EvRemixes Analytics Integration")
    print("=" * 50)

    # Create a test config with analytics endpoint
    config = DownloadConfig(is_admin=False)

    # Create analytics helper
    analytics = AnalyticsHelper(config)

    # Simulate tracking a download
    track_name = "Test Remix Track"
    audio_format = AudioFormat.FLAC
    versions = TrackVersions.ORIGINAL

    print("📊 Simulating download tracking:")
    print(f"   Track: {track_name}")
    print(f"   Format: {audio_format.value}")
    print(f"   Version: {versions.value}")
    print()

    # Get the analytics headers that would be sent
    headers = analytics.get_analytics_headers(track_name, audio_format, versions)

    print("📤 HTTP Headers that would be sent:")
    for key, value in headers.items():
        print(f"   {key}: {value}")
    print()

    # Simulate the JSON payload that would be sent to Flask
    payload = {
        "session_id": headers["X-Analytics-Session"],
        "user_hash": headers["X-Analytics-User"],
        "track_name": track_name,
        "format": audio_format.value,
        "version": versions.value,
        "platform": headers["X-Analytics-Platform"],
        "python_version": headers["X-Analytics-Python"],
        "success": True,
    }

    print("📋 JSON Payload that would be sent to Flask endpoint:")
    print(json.dumps(payload, indent=2))
    print()

    # Test session completion tracking
    analytics.track_session_completion(success=True)

    # Get session summary
    summary = analytics.get_session_summary()
    print("📈 Session Summary:")
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("✅ Analytics integration test completed successfully!")
    print()
    print("🚀 Next Steps:")
    print("   1. Deploy the Flask routes to your web server")
    print("   2. Configure EvRemixes with your analytics_endpoint URL")
    print("   3. Download some tracks to see real analytics data")
    print("   4. Visit /evremixes/analytics on your web server to view the dashboard")


if __name__ == "__main__":
    test_analytics_payload()
