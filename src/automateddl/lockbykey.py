import threading

class LockByKey:
    __locks = dict()
    __selfLock = threading.Lock()

    def getlock(self, key: str) -> threading.Lock:
        with self.__selfLock:
            if not key in self.__locks.keys():
                self.__locks[key] = threading.Lock()
            return self.__locks[key]

    def delete(self, key: str):
        with self.__selfLock:
            if key in self.__locks.keys():
                del self.__locks[key]
