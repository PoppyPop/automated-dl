import aria2p
import os
import pathlib
import patoolib
import shutil
import re
import logging
import threading
import httpx
from typing import Dict, List

from .lockbykey import LockByKey

logger = logging.getLogger(__name__)


class AutomatedDL:
    __api: aria2p.API

    __extractpath: str
    __endedpath: str
    __downpath: str

    __threadlist: Dict[str, threading.Thread] = {}

    __lockbykey: LockByKey = LockByKey()

    # __lock = threading.Lock()

    outSuffix: str = "-OUT"

    def Move(self, path: pathlib.Path, dest: str) -> None:
        to_directory = pathlib.Path(dest)

        # raises FileExistsError when target is already a file
        to_directory.mkdir(parents=True, exist_ok=True)

        shutil.move(str(path), str(to_directory))

    def HandleArchive(self, gid: str, path: pathlib.Path, lockbase: str) -> None:
        logger.info(f"{gid} HandleArchive")

        keepcharacters = (".", "_")
        safeLockbase = "".join(
            c for c in lockbase if c.isalnum() or c in keepcharacters
        ).rstrip()

        baseName = os.path.join(self.__extractpath, safeLockbase)

        outDir = pathlib.Path(baseName + self.outSuffix)

        logger.info(f"{gid} Acquire Lock {safeLockbase}")

        lock = self.__lockbykey.getlock(safeLockbase)

        if not lock.locked() and lock.acquire(timeout=5):
            try:
                if path.exists():
                    outDir.mkdir(parents=True, exist_ok=True)

                    logger.info(f"{gid} Extract")

                    try:
                        patoolib.extract_archive(str(path), outdir=outDir.as_posix())

                        logger.info(f"{gid} Move")
                        self.Move(outDir, self.__endedpath)

                        filetoremove = list(
                            filter(
                                lambda dir: dir.is_file()
                                and dir.name.startswith(lockbase),
                                pathlib.Path(self.__downpath).iterdir(),
                            )
                        )

                        for file in filetoremove:
                            logger.info(f"{gid} Clean {file.name}")
                            os.remove(str(file))

                    except patoolib.util.PatoolError as inst:
                        logger.error(f"{gid} Error {str(inst)}")

                else:
                    logger.warning(f"{gid} Missing file")

            finally:
                logger.info(f"{gid} Lock Release")
                lock.release()
                self.__lockbykey.delete(safeLockbase)

        else:
            logger.warning(f"{gid} Already Locked")

    def HandleMultiPart(
        self, gid: str, api: aria2p.API, path: pathlib.Path, ext: str
    ) -> None:
        multipartRegEx: List[str] = [r"^(?P<filename>.+)\.part(?P<number>\d+)\."]
        doExtract: bool = False
        isMatched: bool = False
        filename: str = path.name

        for regex in multipartRegEx:
            m = re.match(regex + ext[1:] + "$", filename)

            if m is not None:
                isMatched = True
                groupNumber = m.group("number")
                if groupNumber.isnumeric:
                    dls = api.get_downloads()

                    filterdDls = list(
                        filter(
                            lambda download: download.name.startswith(
                                m.group("filename")
                            ),
                            dls,
                        )
                    )

                    if all(e.is_complete for e in filterdDls):
                        doExtract = True
                        filename = m.group("filename")
                        break  # We have all the necessary data

        if not isMatched or doExtract:
            self.HandleArchive(gid, path, filename)

    def HandleDownload(
        self, api: aria2p.API, dl: aria2p.Download, path: pathlib.Path
    ) -> None:
        path = pathlib.Path(os.path.join(self.__downpath, path.name))

        archiveExt: List[str] = [".zip", ".rar"]

        _, file_extension = os.path.splitext(path)
        if file_extension == ".nfo":
            # API + RemoveApi/DeleteApi
            api.remove(downloads=[dl], files=True, clean=True)

        elif any(file_extension == ext for ext in archiveExt):
            # Extract -> MoveFs -> RemoveApi
            self.HandleMultiPart(dl.gid, api, path, file_extension)
            api.remove(downloads=[dl], clean=True)
        else:
            # MoveFs and RemoveApi
            self.Move(path, self.__endedpath)
            api.remove(downloads=[dl], clean=True)

            # Trigger Sonarr/Radarr scan if it's a media file
            if self._is_media_file(path.name):
                if self._is_episode(path.name):
                    self._trigger_sonarr_scan(self.__endedpath)
                else:
                    self._trigger_radarr_scan(self.__endedpath)

    def on_complete_thread(self, api: aria2p.API, gid: str) -> None:
        logger.info(f"{gid} OnComplete")

        dl = api.get_download(gid)

        for file in dl.files:
            self.HandleDownload(api, dl, file.path)

        logger.info(f"{gid} Complete")

    def on_complete(self, api: aria2p.API, gid: str) -> None:
        kwargs = {
            "api": api,
            "gid": gid,
        }

        self.__threadlist[gid] = threading.Thread(
            target=self.on_complete_thread, kwargs=kwargs
        )
        self.__threadlist[gid].start()

    def __init__(
        self,
        api: aria2p.API,
        downpath: str,
        extractpath: str,
        endedpath: str,
        sonarr_url: str = "",
        sonarr_api_key: str = "",
        radarr_url: str = "",
        radarr_api_key: str = "",
    ) -> None:
        self.__api = api
        self.__downpath = downpath
        self.__extractpath = extractpath
        self.__endedpath = endedpath
        self.__sonarr_url = sonarr_url
        self.__sonarr_api_key = sonarr_api_key
        self.__radarr_url = radarr_url
        self.__radarr_api_key = radarr_api_key

        pathlib.Path(downpath).mkdir(parents=True, exist_ok=True)
        pathlib.Path(extractpath).mkdir(parents=True, exist_ok=True)
        pathlib.Path(endedpath).mkdir(parents=True, exist_ok=True)

    def _is_media_file(self, filename: str) -> bool:
        """Check if the file is a media (video) file."""
        media_extensions = [
            ".mkv",
            ".mp4",
            ".avi",
            ".mov",
            ".flv",
            ".wmv",
            ".webm",
            ".m4v",
            ".mpg",
            ".mpeg",
            ".3gp",
            ".ogv",
        ]
        _, ext = os.path.splitext(filename)
        return ext.lower() in media_extensions

    def _is_episode(self, filename: str) -> bool:
        """
        Detect if the media file is an episode or a movie.
        Returns True for episodes, False for movies.
        """
        # Remove extension
        name_without_ext = os.path.splitext(filename)[0]

        # Pattern for Season/Episode: S01E01, s01e01, 1x01, etc.
        episode_patterns = [
            r"[Ss]\d{1,2}[Ee]\d{1,2}",  # S01E01, s01e01
            r"\d{1,2}x\d{1,2}",  # 1x01
        ]

        for pattern in episode_patterns:
            if re.search(pattern, name_without_ext):
                return True

        return False

    def _trigger_sonarr_scan(self, directory: str) -> None:
        """Trigger Sonarr DownloadedEpisodesScan API."""
        if not self.__sonarr_url or not self.__sonarr_api_key:
            logger.debug("Sonarr not configured, skipping scan")
            return

        try:
            url = f"{self.__sonarr_url}/api/v3/command"
            headers = {"X-Api-Key": self.__sonarr_api_key}
            payload = {
                "name": "DownloadedEpisodesScan",
                "path": directory,
            }

            response = httpx.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()

            logger.info(f"Sonarr scan triggered for {directory}")
        except Exception as e:
            logger.error(f"Error triggering Sonarr scan: {str(e)}")

    def _trigger_radarr_scan(self, directory: str) -> None:
        """Trigger Radarr DownloadedMoviesScan API."""
        if not self.__radarr_url or not self.__radarr_api_key:
            logger.debug("Radarr not configured, skipping scan")
            return

        try:
            url = f"{self.__radarr_url}/api/v3/command"
            headers = {"X-Api-Key": self.__radarr_api_key}
            payload = {
                "name": "DownloadedMoviesScan",
                "path": directory,
            }

            response = httpx.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()

            logger.info(f"Radarr scan triggered for {directory}")
        except Exception as e:
            logger.error(f"Error triggering Radarr scan: {str(e)}")

    def start(self) -> None:
        self.__api.listen_to_notifications(
            threaded=True, on_download_complete=self.on_complete
        )
        logger.info("Starting listening")

    def stop(self) -> None:
        self.__api.stop_listening()
        logger.info("Stop listening")

        for th in self.__threadlist.values():
            th.join()

        logger.info("Stop thread")
