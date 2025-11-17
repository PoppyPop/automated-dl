"""Tests for media detection and Sonarr/Radarr API functionality."""

from unittest.mock import Mock, patch, MagicMock
from typing import Any

from src.automateddl import AutomatedDL


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
        self, mock_post: Any, tmp_path: Any, caplog: Any
    ) -> None:
        """Test that downloading an episode triggers Sonarr scan."""
        caplog.set_level("INFO")
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        extractPath = str(tmp_path.joinpath("Extract"))
        endedPath = str(tmp_path.joinpath("Ended"))

        # Create mock API
        mock_api = MagicMock()
        mock_api.get_downloads.return_value = []

        # Create a mock download object for the episode file
        mock_download = MagicMock()
        mock_file = MagicMock()

        # Create the episode file
        source = tmp_path.joinpath("100_S01E02.mkv")
        source.write_bytes(b"1" * 100)

        mock_file.path = source
        mock_download.files = [mock_file]
        mock_api.get_download.return_value = mock_download

        # Create an AutomatedDL with Sonarr configured
        autodl = AutomatedDL(
            mock_api,
            str(tmp_path),
            extractPath,
            endedPath,
            sonarr_url="http://localhost:8989",
            sonarr_api_key="test_key",
        )

        # Call on_complete_thread to process the download
        autodl.on_complete_thread(mock_api, "0000000000000001")

        target = tmp_path.joinpath("Ended").joinpath("series", source.name)

        assert not source.exists()
        assert target.exists()
        assert len(mock_api.get_downloads()) == 0

        # Sonarr API call should be made for episodes
        assert mock_post.call_count == 1

    @patch("httpx.post")
    def test_movie_download_triggers_sonarr(
        self, mock_post: Any, tmp_path: Any, caplog: Any
    ) -> None:
        """Test that downloading a movie triggers Radarr scan."""
        caplog.set_level("INFO")
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        extractPath = str(tmp_path.joinpath("Extract"))
        endedPath = str(tmp_path.joinpath("Ended"))

        # Create mock API
        mock_api = MagicMock()
        mock_api.get_downloads.return_value = []

        # Create a mock download object for the movie file
        mock_download = MagicMock()
        mock_file = MagicMock()

        # Create the movie file
        source = tmp_path.joinpath("100.mkv")
        source.write_bytes(b"1" * 100)

        mock_file.path = source
        mock_download.files = [mock_file]
        mock_api.get_download.return_value = mock_download

        # Create an AutomatedDL with Radarr configured
        autodl = AutomatedDL(
            mock_api,
            str(tmp_path),
            extractPath,
            endedPath,
            radarr_url="http://localhost:8989",
            radarr_api_key="test_key",
        )

        # Call on_complete_thread to process the download
        autodl.on_complete_thread(mock_api, "0000000000000001")

        target = tmp_path.joinpath("Ended").joinpath("movies", source.name)

        assert not source.exists()
        assert target.exists()
        assert len(mock_api.get_downloads()) == 0

        # Radarr API call should be made for movies
        assert mock_post.call_count == 1

    @patch("httpx.post")
    def test_non_media_file_no_api_call(self, mock_post: Any, tmp_path: Any) -> None:
        """Test that non-media files don't trigger API calls."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        extractPath = str(tmp_path.joinpath("Extract"))
        endedPath = str(tmp_path.joinpath("Ended"))

        # Create mock API
        mock_api = MagicMock()
        mock_api.get_downloads.return_value = []

        # Create a mock download object for the text file
        mock_download = MagicMock()
        mock_file = MagicMock()

        # Create the text file (non-media)
        source = tmp_path.joinpath("100.txt")
        source.write_bytes(b"1" * 100)

        mock_file.path = source
        mock_download.files = [mock_file]
        mock_api.get_download.return_value = mock_download

        autodl = AutomatedDL(
            mock_api,
            str(tmp_path),
            extractPath,
            endedPath,
            sonarr_url="http://localhost:8989",
            sonarr_api_key="test_key",
            radarr_url="http://localhost:7878",
            radarr_api_key="test_key",
        )

        # Call on_complete_thread to process the download
        autodl.on_complete_thread(mock_api, "0000000000000001")

        # No API calls should be made for non-media files
        assert mock_post.call_count == 0

    @patch("httpx.post")
    def test_archive_episode_triggers_sonarr(
        self, mock_post: Any, tmp_path: Any
    ) -> None:
        """Zipped episode should extract, move under series, and trigger Sonarr."""
        import shutil
        from pathlib import Path
        from . import STATIC_DIR

        extractPath = str(tmp_path.joinpath("Extract"))
        endedPath = str(tmp_path.joinpath("Ended"))

        # Create mock API
        mock_api = MagicMock()
        mock_api.get_downloads.return_value = []

        # Copy pre-made episode.zip from static dir
        test_zip_source = Path(STATIC_DIR).joinpath("episode.zip")
        source_zip = tmp_path.joinpath("episode.zip")
        shutil.copy(str(test_zip_source), str(source_zip))

        # Mock download pointing to the zip
        mock_download = MagicMock()
        mock_file = MagicMock()
        mock_file.path = source_zip
        mock_download.files = [mock_file]
        mock_api.get_download.return_value = mock_download

        # Patch httpx.post response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        autodl = AutomatedDL(
            mock_api,
            str(tmp_path),
            extractPath,
            endedPath,
            sonarr_url="http://localhost:8989",
            sonarr_api_key="test_key",
        )

        autodl.on_complete_thread(mock_api, "00000000000000AE")

        # Expect moved under series and Sonarr called
        assert tmp_path.joinpath("Ended", "series").exists()
        assert mock_post.call_count == 1

    @patch("httpx.post")
    def test_archive_movie_triggers_radarr(self, mock_post: Any, tmp_path: Any) -> None:
        """Zipped movie should extract, move under movies, and trigger Radarr."""
        import shutil
        from pathlib import Path
        from . import STATIC_DIR

        extractPath = str(tmp_path.joinpath("Extract"))
        endedPath = str(tmp_path.joinpath("Ended"))

        # Create mock API
        mock_api = MagicMock()
        mock_api.get_downloads.return_value = []

        # Copy pre-made movie.zip from static dir
        test_zip_source = Path(STATIC_DIR).joinpath("movie.zip")
        source_zip = tmp_path.joinpath("movie.zip")
        shutil.copy(str(test_zip_source), str(source_zip))

        # Mock download pointing to the zip
        mock_download = MagicMock()
        mock_file = MagicMock()
        mock_file.path = source_zip
        mock_download.files = [mock_file]
        mock_api.get_download.return_value = mock_download

        # Patch httpx.post response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        autodl = AutomatedDL(
            mock_api,
            str(tmp_path),
            extractPath,
            endedPath,
            radarr_url="http://localhost:7878",
            radarr_api_key="test_key",
        )

        autodl.on_complete_thread(mock_api, "00000000000000AF")

        # Expect moved under movies and Radarr called
        assert tmp_path.joinpath("Ended", "movies").exists()
        assert mock_post.call_count == 1

    @patch("httpx.post")
    def test_archive_nested_media_goes_to_others(
        self, mock_post: Any, tmp_path: Any
    ) -> None:
        """Archive with media in subdirectory should go to others (not detected)."""
        import shutil
        from pathlib import Path
        from . import STATIC_DIR

        extractPath = str(tmp_path.joinpath("Extract"))
        endedPath = str(tmp_path.joinpath("Ended"))

        # Create mock API
        mock_api = MagicMock()
        mock_api.get_downloads.return_value = []

        # Copy pre-made nested.zip from static dir
        test_zip_source = Path(STATIC_DIR).joinpath("nested.zip")
        source_zip = tmp_path.joinpath("nested.zip")
        shutil.copy(str(test_zip_source), str(source_zip))

        # Mock download pointing to the zip
        mock_download = MagicMock()
        mock_file = MagicMock()
        mock_file.path = source_zip
        mock_download.files = [mock_file]
        mock_api.get_download.return_value = mock_download

        # Patch httpx.post response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        autodl = AutomatedDL(
            mock_api,
            str(tmp_path),
            extractPath,
            endedPath,
            sonarr_url="http://localhost:8989",
            sonarr_api_key="test_key",
            radarr_url="http://localhost:7878",
            radarr_api_key="test_key",
        )

        autodl.on_complete_thread(mock_api, "00000000000000B0")

        # Expect moved under others (subdirectory not inspected) and no API calls
        assert tmp_path.joinpath("Ended", "others").exists()
        assert mock_post.call_count == 0
