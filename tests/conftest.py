"""Configuration for the pytest test suite."""

import logging
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import requests
from aria2p import API, Client, enable_logger

from . import CONFIGS_DIR, SESSIONS_DIR


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
) -> Generator[subprocess.Popen[bytes] | None, None, None]:
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


@pytest.fixture(autouse=True)
def tests_logs(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Capture all logs to organized test files."""
    # Create logs directory structure: logs/test_file/test_name.log
    log_base = Path("tests/logs")
    log_base.mkdir(exist_ok=True)

    # Get test module name
    module_name = (
        request.module.__name__.split(".")[-1] if request.module else "unknown"
    )
    test_dir = log_base / module_name
    test_dir.mkdir(exist_ok=True)

    # Get test name
    test_name = request.node.name
    log_file = test_dir / f"{test_name}.log"

    # Remove log file if it already exists
    if log_file.exists():
        log_file.unlink()

    # Set up aria2p logging (aria2p uses loguru internally)
    enable_logger(sink=str(log_file), level="TRACE")

    # Set up standard logging for application logs
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # Add handler to root logger
    logging.root.addHandler(file_handler)
    logging.root.setLevel(logging.DEBUG)

    yield

    # Clean up handler
    logging.root.removeHandler(file_handler)
    file_handler.close()


class _Aria2Server:
    def __init__(
        self,
        tmp_dir: Path,
        port: int,
        config: Path | None = None,
        session: Any | None = None,
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
        self.process: subprocess.Popen[bytes] | None = None

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

    def rmdir(self, directory: Path | None = None) -> None:
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
        config: Path | None = None,
        session: Any | None = None,
        secret: str = "",
    ) -> None:
        self.server = _Aria2Server(tmp_dir, port, config, session, secret)

    def __enter__(self) -> _Aria2Server:
        self.server.start()
        return self.server

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.server.destroy(force=True)
