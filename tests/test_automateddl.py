"""Tests for the `automateddl` module."""

import threading
import time
import os.path
import pathlib
import shutil

import pytest

from . import CONFIGS_DIR, STATIC_DIR
from .conftest import Aria2Server

from src.automateddl import AutomatedDL


def test_nfo_dl(tmp_path, port, capsys):
    with Aria2Server(tmp_path, port, session="very-small-download-nfo.txt") as server:

        extractPath = os.path.join(tmp_path, 'Extract')
        endedPath = os.path.join(tmp_path, 'Ended')

        autodl = AutomatedDL(server.api, tmp_path, extractPath, endedPath)
        autodl.start()

        time.sleep(1)

        server.api.resume_all()
        time.sleep(1)

        autodl.stop()

        download = server.api.get_downloads()

        source = pathlib.Path(os.path.join(tmp_path, '100.nfo'))
        target = pathlib.Path(os.path.join(endedPath, source.name))

        assert not source.exists()
        assert not target.exists()
        assert len(download) == 0

        assert "0000000000000001 Complete" in capsys.readouterr().out

def test_txt_dl(tmp_path, port, capsys):
    with Aria2Server(tmp_path, port, session="very-small-download.txt") as server:

        extractPath = os.path.join(tmp_path, 'Extract')
        endedPath = os.path.join(tmp_path, 'Ended')

        autodl = AutomatedDL(server.api, tmp_path, extractPath, endedPath)
        autodl.start()

        time.sleep(1)

        server.api.resume_all()
        

        time.sleep(1)

        autodl.stop()

        download = server.api.get_downloads()

        source = pathlib.Path(os.path.join(tmp_path, '100.txt'))
        target = pathlib.Path(os.path.join(endedPath, source.name))

        assert not source.exists()
        assert target.exists()
        assert len(download) == 0

        assert "0000000000000001 Complete" in capsys.readouterr().out

def test_zip_dl(tmp_path, port, capsys):
    with Aria2Server(tmp_path, port, session="zip.txt") as server:

        extractPath = os.path.join(tmp_path, 'Extract')
        endedPath = os.path.join(tmp_path, 'Ended')

        autodl = AutomatedDL(server.api, tmp_path, extractPath, endedPath)
        autodl.start()

        time.sleep(1)

        server.api.resume_all()
        

        time.sleep(1)

        autodl.stop()

        download = server.api.get_downloads()

        filename = 'simple.zip'

        source = pathlib.Path(os.path.join(tmp_path, filename))

        extract = pathlib.Path(extractPath)

        target = pathlib.Path(os.path.join(endedPath, source.name+autodl.outSuffix))

        assert not source.exists() # origin file is deleted
        assert len([path for path in extract.iterdir()]) == 0 # extract dir is empty
        assert target.exists() and target.is_dir() # target dir exist

        destFileName = 'simple.txt'

        # dst file is the same
        with open(os.path.join(target, destFileName)) as source_cstream:
            with open(os.path.join(STATIC_DIR, destFileName)) as target_stream:
                source_contents = source_cstream.read()
                target_contents = target_stream.read()
                assert source_contents == target_contents

        assert len(download) == 0 # No remaining download

        assert "0000000000000001 Complete" in capsys.readouterr().out

def test_rar_dl(tmp_path, port, capsys):
    with Aria2Server(tmp_path, port, session="rar.txt") as server:

        extractPath = os.path.join(tmp_path, 'Extract')
        endedPath = os.path.join(tmp_path, 'Ended')

        autodl = AutomatedDL(server.api, tmp_path, extractPath, endedPath)
        autodl.start()

        time.sleep(1)

        server.api.resume_all()
        

        time.sleep(1)

        autodl.stop()

        download = server.api.get_downloads()

        filename = 'simple.rar'

        source = pathlib.Path(os.path.join(tmp_path, filename))

        extract = pathlib.Path(extractPath)

        target = pathlib.Path(os.path.join(endedPath, source.name+autodl.outSuffix))

        assert not source.exists() # origin file is deleted
        assert len([path for path in extract.iterdir()]) == 0 # extract dir is empty
        assert target.exists() and target.is_dir() # target dir exist

        destFileName = 'simple.txt'

        # dst file is the same
        with open(os.path.join(target, destFileName)) as source_cstream:
            with open(os.path.join(STATIC_DIR, destFileName)) as target_stream:
                source_contents = source_cstream.read()
                target_contents = target_stream.read()
                assert source_contents == target_contents

        assert len(download) == 0 # No remaining download

        assert "0000000000000001 Complete" in capsys.readouterr().out

def test_multi_dl(tmp_path, port, capsys):
    with Aria2Server(tmp_path, port, session="multi-rar.txt") as server:

        extractPath = os.path.join(tmp_path, 'Extract')
        endedPath = os.path.join(tmp_path, 'Ended')

        autodl = AutomatedDL(server.api, tmp_path, extractPath, endedPath)
        autodl.start()

        time.sleep(1)

        server.api.resume_all()
        

        time.sleep(1)

        autodl.stop()

        download = server.api.get_downloads()

        filename1 = 'multi.part1.rar'
        filename2 = 'multi.part2.rar'
        filename3 = 'multi.part3.rar'
        filename4 = 'multi.part4.rar'

        source1 = pathlib.Path(os.path.join(tmp_path, filename1))
        source2 = pathlib.Path(os.path.join(tmp_path, filename2))
        source3 = pathlib.Path(os.path.join(tmp_path, filename3))
        source4 = pathlib.Path(os.path.join(tmp_path, filename4))

        extract = pathlib.Path(extractPath)

        target = pathlib.Path(os.path.join(endedPath, "multi"+autodl.outSuffix))

        assert not source1.exists() and not source2.exists() and not source3.exists() and not source4.exists() # origin file is deleted
        assert len([path for path in extract.iterdir()]) == 0 # extract dir is empty
        assert target.exists() and target.is_dir() # target dir exist

        destFileName = 'simple.txt'

        # dst file is the same
        with open(os.path.join(target, destFileName)) as source_cstream:
            with open(os.path.join(STATIC_DIR, destFileName)) as target_stream:
                source_contents = source_cstream.read()
                target_contents = target_stream.read()
                assert source_contents == target_contents

        assert len(download) == 0 # No remaining download

        outvalue = capsys.readouterr().out

        assert "0000000000000001 Complete" in outvalue
        assert "0000000000000002 Complete" in outvalue
        assert "0000000000000003 Complete" in outvalue
        assert "0000000000000004 Complete" in outvalue

def test_missing_dl(tmp_path, port, capsys):
    with Aria2Server(tmp_path, port, session="multi-rar-missing.txt") as server:

        extractPath = os.path.join(tmp_path, 'Extract')
        endedPath = os.path.join(tmp_path, 'Ended')

        autodl = AutomatedDL(server.api, tmp_path, extractPath, endedPath)
        autodl.start()

        time.sleep(1)

        server.api.resume_all()
        
        time.sleep(1)

        autodl.stop()

        download = server.api.get_downloads()

        filename1 = 'multi.part1.rar'
        filename2 = 'multi.part2.rar'
        filename3 = 'multi.part3.rar'
        filename4 = 'multi.part4.rar'

        source1 = pathlib.Path(os.path.join(tmp_path, filename1))
        source2 = pathlib.Path(os.path.join(tmp_path, filename2))
        source3 = pathlib.Path(os.path.join(tmp_path, filename3))
        source4 = pathlib.Path(os.path.join(tmp_path, filename4))

        extract = pathlib.Path(extractPath)

        target = pathlib.Path(os.path.join(endedPath, "multi"+autodl.outSuffix))

        assert source1.exists() and not source2.exists() and source3.exists() and not source4.exists() # origin file is deleted
        assert len([path for path in extract.iterdir()]) == 1 # extract dir is empty

        assert extract.joinpath("multi"+autodl.outSuffix).exists()
        
        assert not target.exists() # target dir not exist

        assert len(download) == 0 # No remaining download

        outvalue = capsys.readouterr().out

        assert "0000000000000001 Complete" in outvalue
        assert "0000000000000003 Complete" in outvalue
        
def test_all_dl(tmp_path, port, capsys):
    with Aria2Server(tmp_path, port, session="all.txt") as server:

        extractPath = os.path.join(tmp_path, 'Extract')
        endedPath = os.path.join(tmp_path, 'Ended')

        autodl = AutomatedDL(server.api, tmp_path, extractPath, endedPath)
        autodl.start()

        time.sleep(1)

        server.api.resume_all()
        

        time.sleep(1)

        autodl.stop()

        download = server.api.get_downloads()

        filename1 = 'multi.part1.rar'
        filename2 = 'multi.part2.rar'
        filename3 = 'multi.part3.rar'
        filename4 = 'multi.part4.rar'
        filename5 = 'simple.rar'
        filename6 = 'simple.zip'
        filename7 = '100.txt'

        source1 = pathlib.Path(os.path.join(tmp_path, filename1))
        source2 = pathlib.Path(os.path.join(tmp_path, filename2))
        source3 = pathlib.Path(os.path.join(tmp_path, filename3))
        source4 = pathlib.Path(os.path.join(tmp_path, filename4))

        source5 = pathlib.Path(os.path.join(tmp_path, filename5))
        source6 = pathlib.Path(os.path.join(tmp_path, filename6))
        source7 = pathlib.Path(os.path.join(tmp_path, filename7))

        extract = pathlib.Path(extractPath)

        target1 = pathlib.Path(os.path.join(endedPath, "multi"+autodl.outSuffix))

        target5 = pathlib.Path(os.path.join(endedPath, source5.name+autodl.outSuffix))
        target6 = pathlib.Path(os.path.join(endedPath, source6.name+autodl.outSuffix))
        target7 = pathlib.Path(os.path.join(endedPath, source7.name))

        assert not source1.exists() and not source2.exists() and not source3.exists() and not source4.exists() # origin file is deleted
        assert not source5.exists() and not source6.exists() and not source7.exists()  # origin file is deleted
        
        assert len([path for path in extract.iterdir()]) == 0 # extract dir is empty
        assert target1.exists() and target1.is_dir() # target dir exist

        assert target5.exists() and target5.is_dir() # target dir exist
        assert target6.exists() and target6.is_dir() # target dir exist

        assert target7.exists() and target7.is_file() # target dir exist

        destFileName = 'simple.txt'

        # dst file is the same
        with open(os.path.join(STATIC_DIR, destFileName)) as target_stream:
            target_contents = target_stream.read()

            with open(os.path.join(target1, destFileName)) as source_cstream:
                source_contents = source_cstream.read()
                assert source_contents == target_contents

            with open(os.path.join(target5, destFileName)) as source_cstream:
                source_contents = source_cstream.read()
                assert source_contents == target_contents

            with open(os.path.join(target6, destFileName)) as source_cstream:
                source_contents = source_cstream.read()
                assert source_contents == target_contents

        assert len(download) == 0 # No remaining download

        outvalue = capsys.readouterr().out

        assert "0000000000000001 Complete" in outvalue
        assert "0000000000000002 Complete" in outvalue
        assert "0000000000000003 Complete" in outvalue
        assert "0000000000000004 Complete" in outvalue
        assert "0000000000000005 Complete" in outvalue
        assert "0000000000000006 Complete" in outvalue
        assert "0000000000000007 Complete" in outvalue