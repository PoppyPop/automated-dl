"""Tests for media detection and Sonarr/Radarr API functionality."""

import os
import pathlib
from unittest.mock import Mock, patch, MagicMock
from typing import Any

from src.automateddl import AutomatedDL
from .conftest import Aria2Server


class TestMediaDetection:
    """Test suite for media file detection."""

    def test_is_media_file_mkv(self) -> None:
        """Test detection of MKV video files."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_media_file("episode.mkv") is True

    def test_is_media_file_mp4(self) -> None:
        """Test detection of MP4 video files."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_media_file("movie.mp4") is True

    def test_is_media_file_avi(self) -> None:
        """Test detection of AVI video files."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_media_file("video.avi") is True

    def test_is_media_file_mov(self) -> None:
        """Test detection of MOV video files."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_media_file("clip.mov") is True

    def test_is_media_file_webm(self) -> None:
        """Test detection of WEBM video files."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_media_file("video.webm") is True

    def test_is_media_file_non_media(self) -> None:
        """Test that non-media files are not detected as media."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_media_file("archive.zip") is False
        assert autodl._is_media_file("document.pdf") is False
        assert autodl._is_media_file("image.jpg") is False

    def test_is_media_file_case_insensitive(self) -> None:
        """Test that extension detection is case-insensitive."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_media_file("video.MKV") is True
        assert autodl._is_media_file("Movie.MP4") is True
        assert autodl._is_media_file("CLIP.AVI") is True


class TestEpisodeDetection:
    """Test suite for episode vs movie detection."""

    def test_is_episode_s_pattern(self) -> None:
        """Test detection of S01E01 pattern."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_episode("Show.Name.S01E01.mkv") is True

    def test_is_episode_lowercase_pattern(self) -> None:
        """Test detection of s01e01 pattern."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_episode("show.name.s01e01.mkv") is True

    def test_is_episode_mixed_case_pattern(self) -> None:
        """Test detection of mixed case pattern."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_episode("Show.Name.S01e01.mkv") is True
        assert autodl._is_episode("show.name.s05E12.mkv") is True

    def test_is_episode_numeric_pattern(self) -> None:
        """Test detection of 1x01 pattern."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_episode("Show.Name.1x01.mkv") is True
        assert autodl._is_episode("Show.Name.2x05.mkv") is True
        assert autodl._is_episode("Show.Name.12x34.mkv") is True

    def test_is_episode_movie(self) -> None:
        """Test that movies are not detected as episodes."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_episode("Movie.Title.2021.mkv") is False
        assert autodl._is_episode("Movie.Title.1080p.mkv") is False
        assert autodl._is_episode("Avatar.mkv") is False

    def test_is_episode_high_season_numbers(self) -> None:
        """Test detection of episodes with high season numbers."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_episode("Show.Name.S10E05.mkv") is True
        assert autodl._is_episode("Show.Name.S99E99.mkv") is True

    def test_is_episode_with_spaces_and_dots(self) -> None:
        """Test episode detection with various separators."""
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        assert autodl._is_episode("Show Name S01E01.mkv") is True
        assert autodl._is_episode("Show-Name-S01E01.mkv") is True
        assert autodl._is_episode("Show_Name_S01E01.mkv") is True


class TestSonarrRadarrAPITrigger:
    """Test suite for Sonarr and Radarr API trigger functionality."""

    def test_sonarr_not_configured(self, caplog: Any) -> None:
        """Test that no API call is made when Sonarr is not configured."""
        caplog.set_level("DEBUG")
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        autodl._trigger_sonarr_scan("/tmp/ended")

        assert "Sonarr not configured, skipping scan" in caplog.text

    def test_radarr_not_configured(self, caplog: Any) -> None:
        """Test that no API call is made when Radarr is not configured."""
        caplog.set_level("DEBUG")
        autodl = AutomatedDL(Mock(), "/tmp", "/tmp/extract", "/tmp/ended")
        autodl._trigger_radarr_scan("/tmp/ended")

        assert "Radarr not configured, skipping scan" in caplog.text

    @patch("httpx.post")
    def test_sonarr_api_call_success(self, mock_post: Any, caplog: Any) -> None:
        """Test successful Sonarr API call."""
        caplog.set_level("INFO")
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        autodl = AutomatedDL(
            Mock(),
            "/tmp",
            "/tmp/extract",
            "/tmp/ended",
            sonarr_url="http://localhost:8989",
            sonarr_api_key="test_key",
        )
        autodl._trigger_sonarr_scan("/tmp/ended")

        # Verify the API call was made with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8989/api/v3/command"
        assert call_args[1]["json"]["name"] == "DownloadedEpisodesScan"
        assert call_args[1]["json"]["path"] == "/tmp/ended"
        assert call_args[1]["headers"]["X-Api-Key"] == "test_key"

        assert "Sonarr scan triggered for /tmp/ended" in caplog.text

    @patch("httpx.post")
    def test_radarr_api_call_success(self, mock_post: Any, caplog: Any) -> None:
        """Test successful Radarr API call."""
        caplog.set_level("INFO")
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        autodl = AutomatedDL(
            Mock(),
            "/tmp",
            "/tmp/extract",
            "/tmp/ended",
            radarr_url="http://localhost:7878",
            radarr_api_key="test_key",
        )
        autodl._trigger_radarr_scan("/tmp/ended")

        # Verify the API call was made with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:7878/api/v3/command"
        assert call_args[1]["json"]["name"] == "DownloadedMoviesScan"
        assert call_args[1]["json"]["path"] == "/tmp/ended"
        assert call_args[1]["headers"]["X-Api-Key"] == "test_key"

        assert "Radarr scan triggered for /tmp/ended" in caplog.text

    @patch("httpx.post")
    def test_sonarr_api_call_failure(self, mock_post: Any, caplog: Any) -> None:
        """Test Sonarr API call error handling."""
        caplog.set_level("ERROR")
        mock_post.side_effect = Exception("Connection error")

    @patch("httpx.post")
    def test_radarr_api_call_failure(self, mock_post: Any, caplog: Any) -> None:
        """Test Radarr API call error handling."""
        caplog.set_level("ERROR")
        mock_post.side_effect = Exception("Connection error")

        autodl = AutomatedDL(
            Mock(),
            "/tmp",
            "/tmp/extract",
            "/tmp/ended",
            radarr_url="http://localhost:7878",
            radarr_api_key="test_key",
        )
        autodl._trigger_radarr_scan("/tmp/ended")

        assert "Error triggering Radarr scan" in caplog.text
        assert "Connection error" in caplog.text

    @patch("httpx.post")
    def test_sonarr_api_call_timeout(self, mock_post: Any, caplog: Any) -> None:
        """Test Sonarr API call with timeout."""
        # Verify that timeout is set to 10 seconds
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        autodl = AutomatedDL(
            Mock(),
            "/tmp",
            "/tmp/extract",
            "/tmp/ended",
            sonarr_url="http://localhost:8989",
            sonarr_api_key="test_key",
        )
        autodl._trigger_sonarr_scan("/tmp/ended")

        # Verify timeout parameter was passed
        call_args = mock_post.call_args
        assert call_args[1]["timeout"] == 10

    @patch("httpx.post")
    def test_radarr_api_call_timeout(self, mock_post: Any, caplog: Any) -> None:
        """Test Radarr API call with timeout."""
        # Verify that timeout is set to 10 seconds
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        autodl = AutomatedDL(
            Mock(),
            "/tmp",
            "/tmp/extract",
            "/tmp/ended",
            radarr_url="http://localhost:7878",
            radarr_api_key="test_key",
        )
        autodl._trigger_radarr_scan("/tmp/ended")

        # Verify timeout parameter was passed
        call_args = mock_post.call_args
        assert call_args[1]["timeout"] == 10


class TestIntegration:
    """Integration tests for the full download and API call flow."""

    @patch("httpx.post")
    def test_episode_download_triggers_sonarr(
        self, mock_post: Any, tmp_path: Any, port: int, caplog: Any
    ) -> None:
        """Test that downloading an episode triggers Sonarr scan."""
        caplog.set_level("INFO")
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with Aria2Server(tmp_path, port, session="episode.txt") as server:
            extractPath = os.path.join(tmp_path, "Extract")
            endedPath = os.path.join(tmp_path, "Ended")

            # Create an AutomatedDL with Sonarr configured
            autodl = AutomatedDL(
                server.api,
                tmp_path,
                extractPath,
                endedPath,
                sonarr_url="http://localhost:8989",
                sonarr_api_key="test_key",
            )
            autodl.start()

            server.api.resume_all()

            Aria2Server.wait_for_downloads_complete(server.api)

            autodl.stop()

            download = server.api.get_downloads()

            source = pathlib.Path(os.path.join(tmp_path, "100_S01E02.mkv"))
            target = pathlib.Path(os.path.join(endedPath, source.name))

            assert not source.exists()
            assert target.exists()
            assert len(download) == 0

            assert "0000000000000001 Complete" in caplog.text

            assert mock_post.call_count == 1

    @patch("httpx.post")
    def test_movie_download_triggers_sonarr(
        self, mock_post: Any, tmp_path: Any, port: int, caplog: Any
    ) -> None:
        """Test that downloading an episode triggers Sonarr scan."""
        caplog.set_level("INFO")
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with Aria2Server(tmp_path, port, session="movie.txt") as server:
            extractPath = os.path.join(tmp_path, "Extract")
            endedPath = os.path.join(tmp_path, "Ended")

            # Create an AutomatedDL with Sonarr configured
            autodl = AutomatedDL(
                server.api,
                tmp_path,
                extractPath,
                endedPath,
                radarr_url="http://localhost:8989",
                radarr_api_key="test_key",
            )
            autodl.start()

            server.api.resume_all()

            Aria2Server.wait_for_downloads_complete(server.api)

            autodl.stop()

            download = server.api.get_downloads()

            source = pathlib.Path(os.path.join(tmp_path, "100.mkv"))
            target = pathlib.Path(os.path.join(endedPath, source.name))

            assert not source.exists()
            assert target.exists()
            assert len(download) == 0

            assert "0000000000000001 Complete" in caplog.text

            assert mock_post.call_count == 1

    @patch("httpx.post")
    def test_non_media_file_no_api_call(
        self, mock_post: Any, tmp_path: Any, port: int
    ) -> None:
        """Test that non-media files don't trigger API calls."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with Aria2Server(tmp_path, port, session="very-small-download.txt") as server:
            extractPath = os.path.join(tmp_path, "Extract")
            endedPath = os.path.join(tmp_path, "Ended")

            autodl = AutomatedDL(
                server.api,
                tmp_path,
                extractPath,
                endedPath,
                sonarr_url="http://localhost:8989",
                sonarr_api_key="test_key",
                radarr_url="http://localhost:7878",
                radarr_api_key="test_key",
            )
            autodl.start()

            server.api.resume_all()

            Aria2Server.wait_for_downloads_complete(server.api)

            autodl.stop()

            # No API calls should be made for non-media files
            assert mock_post.call_count == 0
