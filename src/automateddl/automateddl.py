import aria2p
import os
import pathlib
import patoolib
import shutil
import re
import datetime
import threading

from .lockbykey import LockByKey

class AutomatedDL:
    __api = aria2p.API

    __extractpath = str
    __endedpath = str
    __downpath = str

    __threadlist = {}

    __lockbykey = LockByKey()

    #__lock = threading.Lock()

    outSuffix = '-OUT'

    def Move(self, path: pathlib.Path, dest: str):
        to_directory = pathlib.Path(dest)

        # raises FileExistsError when target is already a file
        to_directory.mkdir(parents=True, exist_ok=True)

        shutil.move(str(path), str(to_directory))

    def HandleArchive(self, gid:str, path: pathlib.Path, lockbase: str):

        print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") + " " + gid + " HandleArchive")

        filename = path.name
        downName = os.path.join(self.__downpath, filename)
        baseName = os.path.join(self.__extractpath, lockbase)
        outDir = pathlib.Path(baseName+self.outSuffix)

        print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") +  " " + gid + " Acquitre Lock " + lockbase)
        
        lock = self.__lockbykey.getlock(lockbase)

        if not lock.locked() and lock.acquire(timeout=0):

            try:
                outDir.mkdir(parents=True, exist_ok=True)

                print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") +  " " + gid + " Extract")

                try:
                    patoolib.extract_archive(downName, outdir=outDir)
               
                    self.Move(outDir, self.__endedpath)

                    filetoremove = list(filter(lambda dir: dir.is_file() and dir.name.startswith(lockbase), 
                        pathlib.Path(self.__downpath).iterdir()))

                    for file in filetoremove:
                        print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") +  " " + gid + " Clean " + file.name)
                        os.remove(str(file))

                except patoolib.util.PatoolError as inst:
                    print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") +  " " + gid + " Error " + str(inst))


            finally:
                print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") + " " + gid + " Lock Release")
                lock.release()
                self.__lockbykey.delete(lockbase)


        else:
            print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") + " " + gid + " Already Locked")

    def HandleMultiPart(self, gid:str, api: aria2p.API, path: pathlib.Path, ext: str):
        multipartRegEx = [r'^(?P<filename>.+)\.part(?P<number>\d+)\.']
        doExtract = False
        isMatched = False
        filename = path.name

        for regex in multipartRegEx:
            m = re.match(regex + ext[1:] + '$', filename)

            if (m != None):
                isMatched = True
                groupNumber = m.group('number')
                if groupNumber.isnumeric:
                    dls = api.get_downloads()

                    filterdDls = list(
                        filter(lambda download: download.name.startswith(m.group('filename')), dls))

                    if all(e.is_complete for e in filterdDls):
                        doExtract = True
                        filename = m.group('filename')
                        break  # We have all the necessary data

        if not isMatched or doExtract:
            self.HandleArchive(gid, path, filename)

    def HandleDownload(self, api: aria2p.API, dl: aria2p.Download, path: pathlib.Path):

        archiveExt = ['.zip', '.rar']

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

    def on_complete_thread(self, api: aria2p.API, gid: str):
        print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") + " " + gid + " OnComplete")

        dl = api.get_download(gid)

        for file in dl.files:
            self.HandleDownload(api, dl, file.path)

        print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") + " " + gid + " Complete")


    def on_complete(self, api: aria2p.API, gid: str):

        kwargs = {
            "api": api,
            "gid": gid,
        }

        self.__threadlist[gid] = threading.Thread(target=self.on_complete_thread, kwargs=kwargs)
        self.__threadlist[gid].start()


    def __init__(self, api: aria2p.API, downpath: str, extractpath: str, endedpath: str):
        self.__api = api
        self.__downpath = downpath
        self.__extractpath = extractpath
        self.__endedpath = endedpath

    def start(self):
        self.__api.listen_to_notifications(
            threaded=True, on_download_complete=self.on_complete)
        print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") + " Starting listenning")

    def stop(self):
        self.__api.stop_listening()
        print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") + " Stop listenning")

        for th in self.__threadlist.values():
            th.join()

        print(datetime.datetime.now().strftime("%Y/%m/%dT%H:%M:%S.%f") + " Stop thread")
