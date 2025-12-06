import threading


class LockByKey:
    __locks: dict[str, threading.Lock] = {}
    __selfLock: threading.Lock = threading.Lock()

    def getlock(self, key: str) -> threading.Lock:
        with self.__selfLock:
            if key not in self.__locks.keys():
                self.__locks[key] = threading.Lock()
            return self.__locks[key]

    def delete(self, key: str) -> None:
        with self.__selfLock:
            if key in self.__locks.keys():
                del self.__locks[key]
