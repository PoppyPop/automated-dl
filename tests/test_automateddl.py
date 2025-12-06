"""Tests for the `automateddl` module."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from src.automateddl import AutomatedDL

from . import STATIC_DIR
from .conftest import Aria2Server


def wait_for_downloads_complete(
    api, timeout: float = 10.0, interval: float = 0.1
) -> bool:
    """Wait until `api.get_downloads()` returns empty or timeout is reached.

    Returns True if downloads completed before timeout, False otherwise.
    """
    waited = 0.0
    while waited < timeout:
        downloads = api.get_downloads()
        if not downloads or len(downloads) == 0:
            return True
        import time as _time

        _time.sleep(interval)
        waited += interval
    return False


def test_nfo_dl(tmp_path: Path, caplog: Any) -> None:
    caplog.set_level("INFO")
    port = 16779
    with Aria2Server(tmp_path, port, session="very-small-download-nfo.txt") as server:
        extractPath = str(tmp_path.joinpath("Extract"))
        endedPath = str(tmp_path.joinpath("Ended"))

        autodl = AutomatedDL(server.api, str(tmp_path), extractPath, endedPath)
        autodl.start()

        server.api.resume_all()

        assert wait_for_downloads_complete(server.api, timeout=30.0)

        download = server.api.get_downloads()

        autodl.stop()
        server.terminate()

        source = tmp_path.joinpath("100.nfo")
        target = Path(endedPath).joinpath(source.name)

        assert not source.exists()
        assert not target.exists()
        assert len(download) == 0

        assert "0000000000000001 Complete" in caplog.text


def test_txt_dl(tmp_path: Path, caplog: Any) -> None:
    """Test text file with mocked Aria2Server."""
    caplog.set_level("INFO")
    extractPath = str(tmp_path.joinpath("Extract"))
    endedPath = str(tmp_path.joinpath("Ended"))

    # Create mock API
    mock_api = MagicMock()
    mock_api.get_downloads.return_value = []

    # Create a mock download object
    mock_download = MagicMock()
    mock_file = MagicMock()
    mock_file.path = tmp_path.joinpath("100.txt")
    mock_download.files = [mock_file]
    mock_api.get_download.return_value = mock_download

    autodl = AutomatedDL(mock_api, str(tmp_path), extractPath, endedPath)

    # Create a test file to simulate download
    source = tmp_path.joinpath("100.txt")
    source.write_text("test content")

    # Call on_complete_thread to process the download
    autodl.on_complete_thread(mock_api, "0000000000000001")

    target = Path(endedPath).joinpath("others", source.name)

    assert not source.exists()
    assert target.exists()
    assert len(mock_api.get_downloads()) == 0


def test_zip_dl(tmp_path: Path, caplog: Any) -> None:
    """Test zip file with mocked Aria2Server."""
    caplog.set_level("INFO")
    extractPath = str(tmp_path.joinpath("Extract"))
    endedPath = str(tmp_path.joinpath("Ended"))

    # Create mock API
    mock_api = MagicMock()
    mock_api.get_downloads.return_value = []

    # Create a mock download object
    mock_download = MagicMock()
    mock_file = MagicMock()

    # Copy the test zip file to tmp_path
    import shutil

    test_zip_source = Path(STATIC_DIR).joinpath("simple.zip")
    source = tmp_path.joinpath("simple.zip")
    shutil.copy(str(test_zip_source), str(source))

    mock_file.path = source
    mock_download.files = [mock_file]
    mock_api.get_download.return_value = mock_download

    autodl = AutomatedDL(mock_api, str(tmp_path), extractPath, endedPath)

    # Call on_complete_thread to process the download
    autodl.on_complete_thread(mock_api, "0000000000000001")

    extract = Path(extractPath)
    target = Path(endedPath).joinpath("others", source.name + autodl.outSuffix)

    assert not source.exists()  # origin file is deleted
    assert len(list(extract.iterdir())) == 0  # extract dir is empty
    assert target.exists() and target.is_dir()  # target dir exist

    destFileName = "simple.txt"

    # dst file is the same
    with open(target.joinpath(destFileName)) as source_cstream:
        with open(Path(STATIC_DIR).joinpath(destFileName)) as target_stream:
            source_contents = source_cstream.read()
            target_contents = target_stream.read()
            assert source_contents.rstrip() == target_contents.rstrip()

    assert len(mock_api.get_downloads()) == 0


def test_rar_dl(tmp_path: Path, caplog: Any) -> None:
    """Test rar file extraction with mocked Aria2Server."""
    caplog.set_level("INFO")
    extractPath = str(tmp_path.joinpath("Extract"))
    endedPath = str(tmp_path.joinpath("Ended"))

    # Create mock API
    mock_api = MagicMock()
    mock_api.get_downloads.return_value = []

    # Create a mock download object
    mock_download = MagicMock()
    mock_file = MagicMock()

    # Copy the test rar file to tmp_path
    import shutil

    test_rar_source = Path(STATIC_DIR).joinpath("simple.rar")
    source = tmp_path.joinpath("simple.rar")
    shutil.copy(str(test_rar_source), str(source))

    mock_file.path = source
    mock_download.files = [mock_file]
    mock_api.get_download.return_value = mock_download

    autodl = AutomatedDL(mock_api, str(tmp_path), extractPath, endedPath)

    # Call on_complete_thread to process the download
    autodl.on_complete_thread(mock_api, "0000000000000001")

    extract = Path(extractPath)
    target = Path(endedPath).joinpath("others", source.name + autodl.outSuffix)

    assert not source.exists()  # origin file is deleted
    assert len(list(extract.iterdir())) == 0  # extract dir is empty
    assert target.exists() and target.is_dir()  # target dir exist

    destFileName = "simple.txt"

    # dst file is the same
    with open(target.joinpath(destFileName)) as source_cstream:
        with open(Path(STATIC_DIR).joinpath(destFileName)) as target_stream:
            source_contents = source_cstream.read()
            target_contents = target_stream.read()
            assert source_contents.rstrip() == target_contents.rstrip()

    assert len(mock_api.get_downloads()) == 0


def test_multi_dl(tmp_path: Path, caplog: Any) -> None:
    """Test multi-part rar files with mocked Aria2Server."""
    caplog.set_level("INFO")
    extractPath = str(tmp_path.joinpath("Extract"))
    endedPath = str(tmp_path.joinpath("Ended"))

    # Create mock API
    mock_api = MagicMock()
    mock_api.get_downloads.return_value = []

    # Copy all 4 multi-part rar files to tmp_path
    import shutil

    filenames = [
        "multi.part1.rar",
        "multi.part2.rar",
        "multi.part3.rar",
        "multi.part4.rar",
    ]
    sources = []

    for filename in filenames:
        test_file_source = Path(STATIC_DIR).joinpath(filename)
        source = tmp_path.joinpath(filename)
        shutil.copy(str(test_file_source), str(source))
        sources.append(source)

    # Create mock download objects for each part
    for _, source in zip(
        [
            "0000000000000001",
            "0000000000000002",
            "0000000000000003",
            "0000000000000004",
        ],
        sources,
        strict=False,
    ):
        mock_download = MagicMock()
        mock_file = MagicMock()
        mock_file.path = source
        mock_download.files = [mock_file]

        # Create a side effect function to handle multiple calls with different GIDs
        def get_download_side_effect(gid_arg):
            for gid_val, src in zip(
                [
                    "0000000000000001",
                    "0000000000000002",
                    "0000000000000003",
                    "0000000000000004",
                ],
                sources,
                strict=False,
            ):
                if gid_arg == gid_val:
                    mock_dl = MagicMock()
                    mock_fl = MagicMock()
                    mock_fl.path = src
                    mock_dl.files = [mock_fl]
                    return mock_dl
            return None

        mock_api.get_download.side_effect = get_download_side_effect

    autodl = AutomatedDL(mock_api, str(tmp_path), extractPath, endedPath)

    # Call on_complete_thread for each part
    for gid in [
        "0000000000000001",
        "0000000000000002",
        "0000000000000003",
        "0000000000000004",
    ]:
        autodl.on_complete_thread(mock_api, gid)

    extract = Path(extractPath)
    target = Path(endedPath).joinpath("others", "multi" + autodl.outSuffix)

    # All source files should be deleted
    for source in sources:
        assert not source.exists()

    # Extract dir should be empty
    assert len(list(extract.iterdir())) == 0
    # Target dir should exist
    assert target.exists() and target.is_dir()

    # dst file is the same
    destFileName = "simple.txt"
    with open(target.joinpath(destFileName)) as source_cstream:
        with open(Path(STATIC_DIR).joinpath(destFileName)) as target_stream:
            source_contents = source_cstream.read()
            target_contents = target_stream.read()
            assert source_contents.rstrip() == target_contents.rstrip()

    assert len(mock_api.get_downloads()) == 0


def test_missing_dl(tmp_path: Path, caplog: Any) -> None:
    """Test multi-part rar files with missing parts using mocked Aria2Server."""
    caplog.set_level("INFO")
    extractPath = str(tmp_path.joinpath("Extract"))
    endedPath = str(tmp_path.joinpath("Ended"))

    # Create mock API
    mock_api = MagicMock()
    mock_api.get_downloads.return_value = []

    # Copy only part1 and part3 (missing part2 and part4)
    import shutil

    filenames = ["multi.part1.rar", "multi.part3.rar"]
    sources = []

    for filename in filenames:
        test_file_source = Path(STATIC_DIR).joinpath(filename)
        source = tmp_path.joinpath(filename)
        shutil.copy(str(test_file_source), str(source))
        sources.append(source)

    # Create mock download objects for each part
    gids = ["0000000000000001", "0000000000000003"]

    def get_download_side_effect(gid_arg):
        for gid_val, src in zip(gids, sources, strict=False):
            if gid_arg == gid_val:
                mock_dl = MagicMock()
                mock_fl = MagicMock()
                mock_fl.path = src
                mock_dl.files = [mock_fl]
                return mock_dl
        return None

    mock_api.get_download.side_effect = get_download_side_effect

    autodl = AutomatedDL(mock_api, str(tmp_path), extractPath, endedPath)

    # Call on_complete_thread for each available part
    for gid in gids:
        autodl.on_complete_thread(mock_api, gid)

    extract = Path(extractPath)
    target = Path(endedPath).joinpath("others", "multi" + autodl.outSuffix)

    # When extraction fails, source files remain (not deleted)
    assert sources[0].exists()  # part1 remains
    assert sources[1].exists()  # part3 remains

    # When extraction fails due to missing parts, files end up in extract dir
    assert (
        len(list(extract.iterdir())) == 1
    )  # extract dir has the failed extraction dir
    assert extract.joinpath("multi" + autodl.outSuffix).exists()

    # Target dir should not exist (extraction failed)
    assert not target.exists()

    assert len(mock_api.get_downloads()) == 0


def test_all_dl(tmp_path: Path, caplog: Any) -> None:
    """Test all file types (rar, zip, txt) with mocked Aria2Server."""
    caplog.set_level("INFO")
    extractPath = str(tmp_path.joinpath("Extract"))
    endedPath = str(tmp_path.joinpath("Ended"))

    # Create mock API
    mock_api = MagicMock()
    mock_api.get_downloads.return_value = []

    # Copy test files to tmp_path
    import shutil

    # Archive files
    archive_files = {
        "0000000000000001": "multi.part1.rar",
        "0000000000000002": "multi.part2.rar",
        "0000000000000003": "multi.part3.rar",
        "0000000000000004": "multi.part4.rar",
        "0000000000000005": "simple.rar",
        "0000000000000006": "simple.zip",
    }

    # Simple text/media files (non-archive)
    simple_files = {
        "0000000000000007": "100.txt",
        "0000000000000008": "100.mkv",
        "0000000000000009": "100_S01E02.mkv",
    }

    # Copy archive files
    sources = {}
    for gid, filename in archive_files.items():
        test_file_source = Path(STATIC_DIR).joinpath(filename)
        source = tmp_path.joinpath(filename)
        shutil.copy(str(test_file_source), str(source))
        sources[gid] = (source, True)  # True = is archive

    # Create simple files for non-archive downloads
    for gid, filename in simple_files.items():
        source = tmp_path.joinpath(filename)
        source.write_text("test file content")
        sources[gid] = (source, False)  # False = not archive

    def get_download_side_effect(gid_arg):
        if gid_arg in sources:
            mock_dl = MagicMock()
            mock_fl = MagicMock()
            mock_fl.path = sources[gid_arg][0]
            mock_dl.files = [mock_fl]
            return mock_dl
        return None

    mock_api.get_download.side_effect = get_download_side_effect

    autodl = AutomatedDL(mock_api, str(tmp_path), extractPath, endedPath)

    # Call on_complete_thread for all downloads
    for gid in sources.keys():
        autodl.on_complete_thread(mock_api, gid)

    extract = Path(extractPath)
    target1 = Path(endedPath).joinpath("others", "multi" + autodl.outSuffix)
    target5 = Path(endedPath).joinpath("others", "simple.rar" + autodl.outSuffix)
    target6 = Path(endedPath).joinpath("others", "simple.zip" + autodl.outSuffix)
    target7 = Path(endedPath).joinpath("others", "100.txt")  # txt file, not extracted

    # All source files should be deleted
    for _, (source, _) in sources.items():
        assert not source.exists(), f"Source {source.name} still exists"

    # Extract dir should be empty
    assert len(list(extract.iterdir())) == 0

    # All archive targets should exist and be directories
    assert target1.exists() and target1.is_dir()
    assert target5.exists() and target5.is_dir()
    assert target6.exists() and target6.is_dir()

    # Text file target should exist as a file (not extracted)
    assert target7.exists() and target7.is_file()

    # Verify extracted content from archives
    destFileName = "simple.txt"
    with open(Path(STATIC_DIR).joinpath(destFileName)) as target_stream:
        target_contents = target_stream.read()

        with open(target1.joinpath(destFileName)) as source_cstream:
            source_contents = source_cstream.read()
            assert source_contents.rstrip() == target_contents.rstrip()

        with open(target5.joinpath(destFileName)) as source_cstream:
            source_contents = source_cstream.read()
            assert source_contents.rstrip() == target_contents.rstrip()

        with open(target6.joinpath(destFileName)) as source_cstream:
            source_contents = source_cstream.read()
            assert source_contents.rstrip() == target_contents.rstrip()

    assert len(mock_api.get_downloads()) == 0


def test_websocket_failure(tmp_path: Path, caplog: Any) -> None:
    """Test that AutomatedDL handles websocket connection failures with retry logic."""
    import time

    caplog.set_level("INFO")
    extractPath = str(tmp_path.joinpath("Extract"))
    endedPath = str(tmp_path.joinpath("Ended"))

    # Create mock API
    mock_api = MagicMock()
    mock_api.get_downloads.return_value = []

    # Create a mock listener that fails
    mock_listener = MagicMock()
    mock_listener.is_alive.return_value = False
    mock_api.listener = mock_listener

    # Make listen_to_notifications raise an exception to simulate connection failure
    connection_error = Exception("Connection refused")
    mock_api.listen_to_notifications.side_effect = connection_error

    autodl = AutomatedDL(mock_api, str(tmp_path), extractPath, endedPath)

    # Start should not block and should handle the failure
    autodl.start()

    # Give it time to attempt connection and retry
    time.sleep(2)

    # Stop the autodl instance
    autodl.stop()

    # Verify that connection attempts were logged
    assert "Attempting to connect to aria2" in caplog.text
    assert "Error in listener monitor" in caplog.text
    assert "Retrying in" in caplog.text or "Max retries reached" in caplog.text

    # Verify stop was called
    assert "Stop listening" in caplog.text
    assert "Stop complete" in caplog.text


def test_websocket_reconnection(tmp_path: Path, caplog: Any) -> None:
    """Test that AutomatedDL successfully reconnects after temporary websocket failure."""
    import time

    caplog.set_level("INFO")
    extractPath = str(tmp_path.joinpath("Extract"))
    endedPath = str(tmp_path.joinpath("Ended"))

    # Create mock API
    mock_api = MagicMock()
    mock_api.get_downloads.return_value = []

    # Create a mock listener that starts as dead, then becomes alive
    mock_listener = MagicMock()
    call_count = {"listen": 0, "is_alive": 0}

    def listen_side_effect(*args, **kwargs):
        call_count["listen"] += 1
        if call_count["listen"] == 1:
            # First call fails
            raise Exception("Connection failed")
        # Second call succeeds
        mock_api.listener = mock_listener

    def is_alive_side_effect():
        call_count["is_alive"] += 1
        # Stay alive for a few checks, then die to trigger retry
        if call_count["listen"] == 1:
            return False  # First connection attempt failed
        if call_count["is_alive"] < 3:
            return True  # Second connection is stable for a bit
        return False  # Then dies to end the test

    mock_listener.is_alive.side_effect = is_alive_side_effect
    mock_api.listen_to_notifications.side_effect = listen_side_effect
    mock_api.listener = None

    autodl = AutomatedDL(mock_api, str(tmp_path), extractPath, endedPath)

    # Start should not block
    autodl.start()

    # Give it time to attempt connection, fail, retry, and reconnect
    time.sleep(3)

    # Stop the autodl instance
    autodl.stop()

    # Verify that multiple connection attempts were made
    assert caplog.text.count("Attempting to connect to aria2") >= 2
    assert "Retrying in" in caplog.text

    # Verify stop was called
    assert "Stop listening" in caplog.text
    assert "Stop complete" in caplog.text
