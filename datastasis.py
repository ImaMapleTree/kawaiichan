import os
import pickle
from multiprocessing import shared_memory, Process, Queue
import time
import psutil


class NoStasisError(Exception):
    def __init__(self):
        super().__init__("Method requires prior-stasis through means such as Stasis.store().")


class DataLargerThanStasisError(Exception):
    def __init__(self, input_bytes, stasis_bytes):
        super().__init__(f"Stasis updates must contain data that is less than or equal to the initial data in bytes."
                         f"({input_bytes} > {stasis_bytes})")


class NoNameDeclaredError(Exception):
    def __init__(self):
        super().__init__(
            "When accessing stasis data, a name MUST be declared prior to access. (Or created through Stasis.store())")


class PersistentProcess(Process):
    def __init__(self, data, queue: Queue, *args, **kwargs):
        self.shm_name = kwargs.pop("name", None)
        self.wait_time = kwargs.pop("wait_time", 5)
        super(PersistentProcess, self).__init__(*args, **kwargs)
        self.data = data
        self.queue = queue


    def run(self):
        self.raw_data = {"data": self.data, "pid": os.getpid()}
        self.data = pickle.dumps(self.raw_data)
        try: self.shm = shared_memory.SharedMemory(name=self.shm_name, create=True, size=len(self.data))
        except OSError:
            self.shm = shared_memory.SharedMemory(name=self.shm_name)
            self.shm.close()
            self.shm.unlink()
            # Attempts to use the same shm_name again after unlinking the previous one,
            # if this doesn't work uses new name in place.
            try: self.shm = shared_memory.SharedMemory(name=self.shm_name, create=True, size=len(self.data))
            except OSError:
                self.shm = shared_memory.SharedMemory(create=True, size=len(self.data))
        self.shm_name = self.shm.name
        self.queue.put(self.shm_name)
        self.queue.put(len(self.data))
        self.queue.put(os.getpid())
        while True:
            self.shm.buf[0:len(self.data)] = self.data
            time.sleep(self.wait_time)
            if not self.queue.empty():
                self.data = self.queue.get()


class StasisMetaclass(type):
    _names = {}

    def __call__(cls, *args, **kwargs):
        name = kwargs.get("name", None)
        if name not in cls._names or name is None:
            cls._names[name] = super(StasisMetaclass, cls).__call__(*args, **kwargs)
        return cls._names[name]


class Stasis(metaclass=StasisMetaclass):
    def __init__(self, *, name=None, wait_time=5):
        self.name = name
        self._stasis_thread = None
        self._stasis_queue = None
        self._stasis_pid = None
        self.wait_time = wait_time
        self.max_bytes = None
        self._byte_selection = None
        self._shared_memory: shared_memory.SharedMemory = None

    def access_raw(self):
        if not self.name:
            raise NoNameDeclaredError
        if not self._shared_memory:
            self._shared_memory = shared_memory.SharedMemory(name=self.name)
        byte_end = len(self._shared_memory.buf) if not self._byte_selection else self._byte_selection
        return self._shared_memory.buf.tobytes()[0:byte_end]

    def access(self):
        raw = self.access_raw()
        data = pickle.loads(raw)
        self._stasis_pid = data["pid"]
        return data["data"]

    def has_memory(self):
        if not self._shared_memory:
            try: self._shared_memory = shared_memory.SharedMemory(name=self.name)
            except Exception as e: print(e)
        return True


    def store(self, data):
        if self._stasis_thread:
            self._stasis_thread.terminate()
            self._stasis_queue.close()

        if self._shared_memory:
            self._shared_memory.close()
            try: self._shared_memory.unlink()
            except: pass

        self._stasis_queue = Queue()
        self._stasis_thread = PersistentProcess(data, self._stasis_queue, name=self.name,
                                           wait_time=self.wait_time, daemon=True)

        self._stasis_thread.start()
        self.name = self._stasis_queue.get()
        self.max_bytes = self._stasis_queue.get()
        self._stasis_pid = self._stasis_queue.get()
        self._shared_memory = shared_memory.SharedMemory(name=self.name)

        return self.name

    def terminate(self):
        if not self._stasis_pid:
            self._stasis_pid = self.access()["pid"]
        p = psutil.Process(self._stasis_pid)
        p.terminate()
        if self._shared_memory:
            self._shared_memory.close()
            try: self._shared_memory.unlink()
            except: pass
        if self._stasis_thread:
            self._stasis_thread.terminate()
            self._stasis_queue.close()

    def update(self, data, ignore_errors=True):
        if not self._stasis_thread and not ignore_errors:
            raise NoStasisError
        else:
            self.store(data)
        pickled = pickle.dumps({"data": data, "pid": self._stasis_pid})
        if len(pickled) > self.max_bytes and not ignore_errors:
            raise DataLargerThanStasisError(pickled, self.max_bytes)
        else:
            self.store(data)
        if len(pickled) < self.max_bytes:
            self._byte_selection = len(pickled)
        self._stasis_queue.put(pickled)
