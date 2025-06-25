"""Analytics viewer for displaying download statistics."""

from __future__ import annotations

import json
import operator
from pathlib import Path
from typing import Any

from polykit.text import print_color


class AnalyticsViewer:
    """Viewer for analytics data."""

    def __init__(self, analytics_file: Path | None = None) -> None:
        """Initialize the analytics viewer.

        Args:
            analytics_file: Path to analytics data file. If None, uses default location.
        """
        self.analytics_file = analytics_file or Path.home() / ".evremixes" / "analytics.json"
        self.analytics_file.parent.mkdir(exist_ok=True)

    def save_session_data(self, session_data: dict[str, Any]) -> None:
        """Save session data to analytics file.

        Args:
            session_data: Session analytics data to save
        """
        try:
            # Load existing data
            existing_data = []
            if self.analytics_file.exists():
                with self.analytics_file.open() as f:
                    existing_data = json.load(f)

            # Add new session data
            existing_data.append(session_data)

            # Keep only last 100 sessions to avoid file bloat
            if len(existing_data) > 100:
                existing_data = existing_data[-100:]

            # Save updated data
            with self.analytics_file.open("w") as f:
                json.dump(existing_data, f, indent=2)

        except Exception:
            # Don't let analytics failures affect the main functionality
            pass

    def display_stats(self) -> None:
        """Display analytics statistics."""
        try:
            if not self.analytics_file.exists():
                print_color("No analytics data found.", "yellow")
                return

            with self.analytics_file.open() as f:
                sessions = json.load(f)

            if not sessions:
                print_color("No analytics data found.", "yellow")
                return

            total_sessions = len(sessions)
            total_downloads = sum(session.get("total_downloads", 0) for session in sessions)
            successful_downloads = sum(
                session.get("successful_downloads", 0) for session in sessions
            )

            # Platform breakdown
            platforms = {}
            formats = {}
            versions = {}

            for session in sessions:
                platform = session.get("platform", "Unknown")
                platforms[platform] = platforms.get(platform, 0) + 1

                format_used = session.get("format", "Unknown")
                formats[format_used] = formats.get(format_used, 0) + 1

                version_used = session.get("version", "Unknown")
                versions[version_used] = versions.get(version_used, 0) + 1

            print_color("\n🎵 EvRemixes Download Analytics", "cyan")
            print_color("=" * 35, "cyan")

            print_color("\n📊 Overall Statistics:", "green")
            print_color(f"  • Total Sessions: {total_sessions}", "white")
            print_color(f"  • Total Downloads: {total_downloads}", "white")
            print_color(f"  • Successful Downloads: {successful_downloads}", "white")
            if total_downloads > 0:
                success_rate = (successful_downloads / total_downloads) * 100
                print_color(f"  • Success Rate: {success_rate:.1f}%", "white")

            print_color("\n💻 Platform Breakdown:", "green")
            for platform, count in sorted(
                platforms.items(), key=operator.itemgetter(1), reverse=True
            ):
                print_color(f"  • {platform}: {count} sessions", "white")

            print_color("\n🎧 Format Preferences:", "green")
            for format_name, count in sorted(
                formats.items(), key=operator.itemgetter(1), reverse=True
            ):
                print_color(f"  • {format_name}: {count} sessions", "white")

            print_color("\n🎼 Version Preferences:", "green")
            for version, count in sorted(
                versions.items(), key=operator.itemgetter(1), reverse=True
            ):
                print_color(f"  • {version}: {count} sessions", "white")

            # Recent activity
            recent_sessions = sessions[-5:]
            print_color("\n🕒 Recent Activity (Last 5 Sessions):", "green")
            for i, session in enumerate(reversed(recent_sessions), 1):
                downloads = session.get("successful_downloads", 0)
                platform = session.get("platform", "Unknown")
                format_used = session.get("format", "Unknown")
                print_color(f"  {i}. {downloads} downloads on {platform} ({format_used})", "white")

            print_color("\n" + "=" * 35, "cyan")

        except Exception as e:
            print_color(f"Error reading analytics data: {e}", "red")


def main() -> None:
    """Display analytics statistics."""
    viewer = AnalyticsViewer()
    viewer.display_stats()


if __name__ == "__main__":
    main()
