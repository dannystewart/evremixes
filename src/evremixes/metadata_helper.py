#!/usr/bin/env python3

from __future__ import annotations

from typing import TYPE_CHECKING

from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover

if TYPE_CHECKING:
    from pathlib import Path

    from evremixes.types import AlbumInfo, TrackMetadata


class MetadataHelper:
    """Helper class for applying metadata to downloaded tracks."""

    def __init__(self, instrumentals: bool = False) -> None:
        self.enable_instrumentals = instrumentals

    def apply_metadata(
        self, track: TrackMetadata, album_info: AlbumInfo, output_path: Path, cover_data: bytes
    ) -> bool:
        """Add metadata and cover art to the downloaded track file.

        Args:
            track: Track details.
            album_info: Metadata for the album.
            output_path: The path of the downloaded track file.
            cover_data: The cover art, resized and encoded as JPEG.

        Returns:
            True if metadata was added successfully, False otherwise.
        """
        try:
            audio_format = output_path.suffix[1:].lower()
            track_number = str(track.track_number).zfill(2)
            disc_number = 2 if self.enable_instrumentals else 1

            # Add the Instrumental suffix if enabled
            if self.enable_instrumentals and not track.track_name.endswith(" (Instrumental)"):
                track.track_name += " (Instrumental)"

            # Apply metadata based on the audio format
            if audio_format == "m4a":
                self._apply_alac_metadata(
                    track, album_info, output_path, cover_data, track_number, disc_number
                )
            elif audio_format == "flac":
                self._apply_flac_metadata(
                    track, album_info, output_path, cover_data, track_number, disc_number
                )
            return True
        except Exception:
            return False

    def _apply_alac_metadata(
        self,
        track: TrackMetadata,
        album_info: AlbumInfo,
        output_path: Path,
        cover_data: bytes,
        track_number: str,
        disc_number: int,
    ) -> None:
        """Apply metadata for ALAC files."""
        audio = MP4(output_path)

        # Add the metadata to the track
        audio["trkn"] = [(int(track_number), 0)]
        audio["disk"] = [(disc_number, 0)]
        audio["\xa9nam"] = track.track_name
        audio["\xa9ART"] = album_info.artist_name
        audio["\xa9alb"] = album_info.album_name
        audio["\xa9day"] = str(album_info.year)
        audio["\xa9gen"] = album_info.genre

        # Add the album artist if available
        if album_info.album_artist:
            audio["aART"] = album_info.album_artist

        # Add the cover art to the track
        audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]

        audio.save()

    def _apply_flac_metadata(
        self,
        track: TrackMetadata,
        album_info: AlbumInfo,
        output_path: Path,
        cover_data: bytes,
        track_number: str,
        disc_number: int,
    ) -> None:
        """Apply metadata for FLAC files."""
        audio = FLAC(output_path)

        # Add the metadata to the track
        audio["tracknumber"] = track_number
        audio["discnumber"] = str(disc_number)
        audio["title"] = track.track_name
        audio["artist"] = album_info.artist_name
        audio["album"] = album_info.album_name
        audio["date"] = str(album_info.year)
        audio["genre"] = album_info.genre

        # Add the cover art to the track
        if album_info.album_artist:
            audio["albumartist"] = album_info.album_artist

        # Add the cover art to the track
        pic = Picture()
        pic.data = cover_data
        pic.type = 3
        pic.mime = "image/jpeg"
        pic.width = 800
        pic.height = 800
        audio.add_picture(pic)

        audio.save()
