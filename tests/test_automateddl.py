"""Tests for the `automateddl` module."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from . import STATIC_DIR
from .conftest import Aria2Server

from src.automateddl import AutomatedDL


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

        wait_for_downloads_complete(server.api)

        autodl.stop()

        download = server.api.get_downloads()

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
    assert len([path for path in extract.iterdir()]) == 0  # extract dir is empty
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
    assert len([path for path in extract.iterdir()]) == 0  # extract dir is empty
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
    for gid, source in zip(
        [
            "0000000000000001",
            "0000000000000002",
            "0000000000000003",
            "0000000000000004",
        ],
        sources,
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
    assert len([path for path in extract.iterdir()]) == 0
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
        for gid_val, src in zip(gids, sources):
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
        len([path for path in extract.iterdir()]) == 1
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
    for gid, (source, is_archive) in sources.items():
        assert not source.exists(), f"Source {source.name} still exists"

    # Extract dir should be empty
    assert len([path for path in extract.iterdir()]) == 0

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
