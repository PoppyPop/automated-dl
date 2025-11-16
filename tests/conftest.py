"""Configuration for the pytest test suite."""

import json
import os
import random
import subprocess
import sys
import time
import logging
from pathlib import Path
from typing import List, Optional, Any, Generator

import pytest
import requests

from aria2p import API, Client, enable_logger

from . import CONFIGS_DIR, SESSIONS_DIR


@pytest.fixture(autouse=True)
def setup_logging() -> Generator[None, None, None]:
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    yield
    # Reset logging after each test


@pytest.fixture(autouse=True)
def tests_logs(request: pytest.FixtureRequest) -> None:
    # put logs in tests/logs
    log_path = Path("tests") / "logs"

    # tidy logs in subdirectories based on test module and class names
    module = request.module
    class_ = request.cls
    name = request.node.name + ".log"

    if module:
        log_path /= module.__name__.replace("tests.", "")
    if class_:
        log_path /= class_.__name__

    log_path.mkdir(parents=True, exist_ok=True)

    # append last part of the name and enable logger
    log_path /= name
    if log_path.exists():
        log_path.unlink()
    enable_logger(sink=log_path, level=os.environ.get("PYTEST_LOG_LEVEL", "TRACE"))


def spawn_and_wait_server(port: int = 8779) -> subprocess.Popen[bytes]:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "tests.http_server:app",
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    while True:
        try:
            requests.get(f"http://localhost:{port}/1024")
        except Exception:
            time.sleep(0.1)
        else:
            break
    return process


@pytest.fixture(scope="session", autouse=True)
def http_server(
    tmp_path_factory: pytest.TempPathFactory, worker_id: Any
) -> Generator[Optional[subprocess.Popen[bytes]], None, None]:
    if worker_id == "master":
        # single worker: just run the HTTP server
        process = spawn_and_wait_server()
        yield process
        process.kill()
        process.wait()
        return

    # get the temp directory shared by all workers
    root_tmp_dir = tmp_path_factory.getbasetemp().parent

    # try to get a lock
    lock = root_tmp_dir / "lock"
    try:
        lock.mkdir(exist_ok=False)
    except FileExistsError:
        yield None  # failed, don't run the HTTP server
        return

    # got the lock, run the HTTP server
    process = spawn_and_wait_server()
    yield process
    process.kill()
    process.wait()


class _Aria2Server:
    def __init__(
        self,
        tmp_dir: Path,
        port: int,
        config: Optional[Path] = None,
        session: Optional[Any] = None,
        secret: str = "",
    ) -> None:
        self.tmp_dir = tmp_dir
        self.port = port

        # create the command used to launch an aria2c process
        command = [
            "aria2c",
            f"--dir={self.tmp_dir}",
            "--file-allocation=none",
            "--quiet",
            "--enable-rpc=true",
            f"--rpc-listen-port={self.port}",
        ]
        if config:
            command.append(f"--conf-path={config}")
        else:
            # command.append("--no-conf")
            config = CONFIGS_DIR / "default.conf"
            command.append(f"--conf-path={config}")
        if session:
            if isinstance(session, list):
                session_path = self.tmp_dir / "_session.txt"
                with open(session_path, "w") as stream:
                    stream.write("\n".join(session))
                command.append(f"--input-file={session_path}")
            else:
                session_path = SESSIONS_DIR / session
                if not session_path.exists():
                    raise ValueError(f"no such session: {session}")
                command.append(f"--input-file={session_path}")
        if secret:
            command.append(f"--rpc-secret={secret}")

        self.command = command
        self.process: Optional[subprocess.Popen[bytes]] = None

        # create the client with port
        self.client = Client(port=self.port, secret=secret, timeout=20)

        # create the API instance
        self.api = API(self.client)

    def start(self) -> None:
        while True:
            # create the subprocess
            self.process = subprocess.Popen(self.command)

            # make sure the server is running
            retries = 5
            while retries:
                try:
                    self.client.list_methods()
                except requests.ConnectionError:
                    time.sleep(0.1)
                    retries -= 1
                else:
                    break

            if retries:
                break

    def wait(self) -> None:
        while self.process is not None:
            try:
                self.process.wait()
            except subprocess.TimeoutExpired:
                pass
            else:
                break

    def terminate(self) -> None:
        if self.process is not None:
            self.process.terminate()
            self.wait()

    def kill(self) -> None:
        if self.process is not None:
            self.process.kill()
            self.wait()

    def rmdir(self, directory: Optional[Path] = None) -> None:
        if directory is None:
            directory = self.tmp_dir
        for item in directory.iterdir():
            if item.is_dir():
                self.rmdir(item)
            else:
                item.unlink()
        directory.rmdir()

    def destroy(self, force: bool = False) -> None:
        if force:
            self.kill()
        else:
            self.terminate()
        self.rmdir()


class Aria2Server:
    def __init__(
        self,
        tmp_dir: Path,
        port: int,
        config: Optional[Path] = None,
        session: Optional[Any] = None,
        secret: str = "",
    ) -> None:
        self.server = _Aria2Server(tmp_dir, port, config, session, secret)

    def __enter__(self) -> _Aria2Server:
        self.server.start()
        return self.server

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.server.destroy(force=True)

    @staticmethod
    def wait_for_downloads_complete(
        api, timeout: float = 10.0, interval: float = 0.1
    ) -> bool:
        """Wait until `api.get_downloads()` returns empty or timeout is reached.

        Returns True if downloads completed before timeout, False otherwise.
        """
        waited = 0.0
        while waited < timeout:
            downloads = api.get_downloads()
            if not downloads:
                return True
            time.sleep(interval)
            waited += interval
        return False


ports_file = Path(".ports.json")


def get_lock() -> None:
    lockdir = Path(".lockdir")
    while True:
        try:
            lockdir.mkdir(exist_ok=False)
        except FileExistsError:
            time.sleep(0.025)
        else:
            break


def release_lock() -> None:
    Path(".lockdir").rmdir()


def get_random_port() -> int:
    return random.randint(15000, 16000)


def get_current_ports() -> List[int]:
    try:
        ports: List[int] = json.loads(ports_file.read_text())
        return ports
    except FileNotFoundError:
        return []


def set_current_ports(ports: List[int]) -> None:
    ports_file.write_text(json.dumps(ports))


def reserve_port() -> int:
    get_lock()

    ports = get_current_ports()
    port_number = get_random_port()
    while port_number in ports:
        port_number = get_random_port()
    ports.append(port_number)
    set_current_ports(ports)

    release_lock()
    return port_number


def release_port(port_number: int) -> None:
    get_lock()
    ports = get_current_ports()
    ports.remove(port_number)
    set_current_ports(ports)
    release_lock()


@pytest.fixture
def port() -> Generator[int, None, None]:
    port_number = reserve_port()
    yield port_number
    release_port(port_number)


@pytest.fixture
def server(tmp_path: Path, port: int) -> Generator[_Aria2Server, None, None]:
    with Aria2Server(tmp_path, port) as server:
        yield server
