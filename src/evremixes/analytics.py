"""Analytics helper for tracking remix downloads."""

from __future__ import annotations

import hashlib
import platform
import sys
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import requests
from polykit.log import PolyLog

from evremixes.config import DownloadConfig

if TYPE_CHECKING:
    from logging import Logger

    from evremixes.types import AudioFormat, TrackMetadata, TrackVersions


class AnalyticsHelper:
    """Helper class for tracking download analytics."""

    def __init__(self, config: DownloadConfig) -> None:
        self.config = config
        self.logger: Logger = PolyLog.get_logger()
        self._session_id = str(uuid.uuid4())[:8]  # Short session ID
        self._download_count = 0
        self._successful_downloads = 0

    def get_analytics_headers(
        self, track_name: str, audio_format: AudioFormat, versions: TrackVersions
    ) -> dict[str, str]:
        """Generate analytics headers for download requests.

        Args:
            track_name: Name of the track being downloaded
            audio_format: Audio format being downloaded
            versions: Version type being downloaded

        Returns:
            Dictionary of headers to include in requests
        """
        # Create anonymous user identifier (hashed machine info)
        machine_info = f"{platform.system()}-{platform.machine()}-{platform.python_version()}"
        user_hash = hashlib.sha256(machine_info.encode()).hexdigest()[:12]

        return {
            "User-Agent": f"evremixes/1.0 ({platform.system()}; {platform.machine()})",
            "X-Analytics-Session": self._session_id,
            "X-Analytics-User": user_hash,
            "X-Analytics-Track": track_name,
            "X-Analytics-Format": audio_format.value,
            "X-Analytics-Version": versions.value,
            "X-Analytics-Platform": platform.system(),
            "X-Analytics-Python": platform.python_version(),
        }

    def track_download(
        self,
        track_name: str,
        audio_format: AudioFormat,
        versions: TrackVersions,
        success: bool = True,
    ) -> None:
        """Track an individual track download."""
        self._download_count += 1
        if success:
            self._successful_downloads += 1

        # Send to remote analytics endpoint if configured
        self._send_remote_analytics(track_name, audio_format, versions, success)

    def _send_remote_analytics(
        self,
        track_name: str,
        audio_format: AudioFormat,
        versions: TrackVersions,
        success: bool,
    ) -> None:
        """Send analytics data to remote endpoint."""
        # Check if remote analytics is enabled
        remote_url = DownloadConfig.ANALYTICS_ENDPOINT
        if not remote_url:
            return

        try:
            payload = {
                "session_id": self._session_id,
                "user_hash": self._get_user_hash(),
                "track_name": track_name,
                "format": audio_format.value,
                "version": versions.value,
                "platform": platform.system(),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                "success": success,
            }

            # Send POST request with timeout
            response = requests.post(
                remote_url, json=payload, timeout=5, headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                self.logger.debug("Analytics data sent to remote endpoint")
            else:
                self.logger.warning("Remote analytics failed: %s", response.status_code)

        except Exception as e:
            # Don't let analytics failures affect downloads
            self.logger.debug("Remote analytics error: %s", str(e))

    def _get_user_hash(self) -> str:
        """Get the anonymous user hash."""
        machine_info = f"{platform.system()}-{platform.machine()}-{platform.python_version()}"
        return hashlib.sha256(machine_info.encode()).hexdigest()[:12]

    def track_track_download(self, track: TrackMetadata, audio_format: AudioFormat) -> None:
        """Track an individual track download.

        Args:
            track: The track that was downloaded
            audio_format: Audio format used
        """
        from evremixes.types import TrackVersions

        versions = TrackVersions.ORIGINAL  # Default to original version
        self.track_download(track.track_name, audio_format, versions)

    def track_download_session(self, config: DownloadConfig) -> None:
        """Track a complete download session.

        Args:
            config: Download configuration
        """
        self.logger.info(
            "Download session completed: %s tracks, %s format, %s version - Session: %s",
            self._successful_downloads,
            config.audio_format.value if config.audio_format else "unknown",
            config.versions.value if config.versions else "unknown",
            self._session_id,
        )

        # Save session data for analytics
        self._save_session_data(config)

    def _save_session_data(self, config: DownloadConfig) -> None:
        """Save session data to analytics file.

        Args:
            config: Download configuration
        """
        try:
            from evremixes.analytics_viewer import AnalyticsViewer

            session_data = {
                **self.get_session_summary(),
                "timestamp": datetime.now().astimezone().isoformat(),
                "format": config.audio_format.value if config.audio_format else "unknown",
                "version": config.versions.value if config.versions else "unknown",
            }

            viewer = AnalyticsViewer()
            viewer.save_session_data(session_data)

        except Exception as e:
            # Never let analytics failures affect downloads
            self.logger.debug("Failed to save session data: %s", str(e))

    def send_download_event(
        self,
        track_name: str,
        audio_format: AudioFormat,
        versions: TrackVersions,
        success: bool = True,
    ) -> None:
        """Send a download event to analytics endpoint (optional).

        This is a fire-and-forget request that won't block downloads if it fails.

        Args:
            track_name: Name of the track downloaded
            audio_format: Audio format downloaded
            versions: Version type downloaded
            success: Whether the download was successful
        """
        try:
            # You can implement this to send to your own analytics endpoint
            # For now, we'll just log it locally
            self.logger.info(
                "Download event: %s (%s, %s) - %s",
                track_name,
                audio_format.value,
                versions.value,
                "Success" if success else "Failed",
            )

            # Example of how you could send to your own endpoint:
            # analytics_data = {
            #     "event": "download",
            #     "track": track_name,
            #     "format": audio_format.value,
            #     "version": versions.value,
            #     "success": success,
            #     "session": self._session_id,
            #     "platform": platform.system(),
            #     "timestamp": datetime.now().isoformat()
            # }
            #
            # requests.post(
            #     "https://your-analytics-endpoint.com/events",
            #     json=analytics_data,
            #     timeout=5
            # )

        except Exception as e:
            # Never let analytics failures affect downloads
            self.logger.debug("Analytics event failed: %s", str(e))

    def get_session_summary(self) -> dict[str, str | int]:
        """Get a summary of the current download session.

        Returns:
            Dictionary with session summary data
        """
        success_rate = (
            self._successful_downloads / self._download_count if self._download_count > 0 else 0
        )

        return {
            "session_id": self._session_id,
            "total_downloads": self._download_count,
            "successful_downloads": self._successful_downloads,
            "success_rate": int(success_rate * 100),  # Convert to percentage as int
            "platform": platform.system(),
            "python_version": platform.python_version(),
        }
