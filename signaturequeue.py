import threading
import time
import multiprocessing
import multiprocessing.queues as mpq
import queue as _queue
import uuid

'''
Class by Evan Cowin himself

1/2/2021

Updated:
-CycleQueue and QueueDict (+CheatDict, but we don't talk about that)
6/11/2021

'''

class Empty(_queue.Empty):
	pass

class QueueDict(dict):
	def __init__(self, *args, **kwargs):
		super(QueueDict, self).__init__(*args, **kwargs)
		self._KEYINDEX = []
		self.index = -1
		
	def __setitem__(self, key, value):
		super().__setitem__(key, value)
		if key in self._KEYINDEX: self._KEYINDEX.pop(self._KEYINDEX.index(key))
		self._KEYINDEX.append(key)
		
	def retrieve(self, index):
		return self[self._KEYINDEX[index]]
		
	def next(self):
		self.index = self.index + 1 if self.index + 1 < len(self._KEYINDEX) else 0
		return self.retrieve(self.index)
		
	def __len__(self):
		return len(self._KEYINDEX)
		
class CheatDict(QueueDict): #im angry I did this but I couldn't think of a clean way to accomplish this in the Queue class
	def __init__(self, *args, **kwargs):
		super(CheatDict, self).__init__(*args, **kwargs)
		self.cheat_index = -1
		
	def next(self, type=0):
		if type == 1:
			self.cheat_index = self.cheat_index + 1 if self.cheat_index + 1 < len(self._KEYINDEX) else 0
			return self.retrieve(self.cheat_index)
		else:
			self.index = self.index + 1 if self.index + 1 < len(self._KEYINDEX) else 0
			return self.retrieve(self.index)

class IdentifierTypeError(Exception):
	def __init__(self, id):
		self.id = id
		super().__init__()
		
	def __str__(self):
		return f"{type(self.id)} is not a valid identifier type (Integer or String)"

class InvalidItemError(Exception):
	def __init__(self, item):
		self.item = item
		super().__init__(f"{type(self.item)} is not type {type(Queue.Item())}")

class QueueIdentifierError(Exception):
	def __init__(self):
		super().__init__("Identifier must be specified to get non-bypassed items.")

class Queue(mpq.Queue):
	class Item():
		def __init__(self, id=None, item=None):
			self._valid_identifiers = [type(0), type("string"), type(None)]
			if type(id) not in self._valid_identifiers: raise IdentifierTypeError(id)
			self._id = id
			self._item = item
	
	def __init__(self, id=None, maxsize=0, ctx=None, sentinel=None):
		self.ctx = ctx if ctx is not None else multiprocessing.get_context()
		super(Queue, self).__init__(maxsize=maxsize, ctx=self.ctx)
		self.sentinel = sentinel
		self._id = id
		self._thread_dict = {}
		self._thread_dict[threading.current_thread().ident] = id
		self._valid_identifiers = [type(0), type("string"), type(None)]
		if type(id) not in self._valid_identifiers: raise IdentifierTypeError(id)
		

	def get(self, bypass=False, timeout=None):
		if not hasattr(self, '_valid_identifiers'): self._mpinit_()
		timeout_start = time.time()
		_blocked = True
		
		def safe_put(self, item):
			if self.qsize != None: super().put(item, True, 10)
			else: super().put(item, False)
		
		while _blocked:
			item = super().get(True, timeout)
			if timeout != None:
				if time.time() - timeout_start >= timeout:
					_blocked = False
			
			if bypass == True:
				if type(item) != type(self.Item()): return item #If item isn't a Item, return it as is
				return item._item #If the item IS a Item, return the actual item itself
				
			if self.id() == None: #Signature isn't identified
				safe_put(self, item)
				raise QueueIdentifierError
				return
				
			if type(item) != type(self.Item()): #Item is not a Item
				safe_put(self, item)
				raise InvalidItemError(item)
				return
			
			if self.id()  != item._id:
				safe_put(self, item)
			else:
				return item._item
		
	def get_nowait(self, bypass=False):
		if not hasattr(self, '_valid_identifiers'): self._mpinit_()
		def safe_put(self, item):
			if self.qsize != None: super().put(item, True, 10)
			else: super().put(item, False)
				
		item = super().get(False)
		
		if bypass == True: 
			if type(item) != type(self.Item()):
				return item
			return item._item
			
		if self.id() == None:
			safe_put(self, item)
			raise QueueIdentifierError
			
		if type(item) != type(self.Item()):
			safe_put(self, item)
			raise InvalidItemError(item)
			
		if self.id()  != item._id:
			safe_put(self, item)
		else:
			return item._item
		raise _queue.Empty

	def put_nowait(self, item, id=None, not_item=False):
		if not hasattr(self, '_valid_identifiers'): self._mpinit_()
		if id == None and not_item: return super().put(item, False)
		else: return super().put(self.Item(id, item), True)
		if type(id) not in self._valid_identifiers: raise IdentifierTypeError(id)
		return super().put(self.Item(id, item), False)
	
	def put(self, item, id=None, timeout=None, not_item=False):
		if not hasattr(self, '_valid_identifiers'): self._mpinit_()
		if id == None and not_item: return super().put(item, True, timeout)
		else: return super().put(self.Item(id, item), True, timeout)
		if type(id) not in self._valid_identifiers: raise IdentifierTypeError(id)
		return super().put(self.Item(id, item), True, timeout)

	def _mpinit_(self):
		self._valid_identifiers = [type(0), type("string"), type(None)]

	def assign(self, id=None):
		self._mpinit_()
		current_thread = threading.current_thread()
		if type(id) not in self._valid_identifiers: raise IdentifierTypeError(id)
		if current_thread.name== "MainThread": #Multiprocessing Method
			self._thread_dict[current_thread.ident] = id
			self._id = id
			return self._id
		self._thread_dict[current_thread.ident] = id #Threading Method
		return id
		
	def id(self):
		current_thread = threading.current_thread()
		if current_thread.name == "MainThread": return self._id
		return self._thread_dict.get(current_thread.ident)
		
	def close(self):
		self.put(self.sentinel)
		while self._buffer:
			super().get()
		super().close()
		
class CycleQueue(Queue):
	def __init__(self, *args, **kwargs):
		super(CycleQueue, self).__init__(*args, **kwargs)
		self._thread_dict = CheatDict()
		self._thread_dict[threading.current_thread().ident] = self._id
		self.ret_id = self._id
		self.cycle_sleep = 0.1
		
	def cycle_put(self, item, id=None, timeout=None, not_item=False):
		if id: return super.put(item, id, timeout, not_item)
		_id = self._thread_dict.next()
		id = _id if _id != self._id else self._thread_dict.next()
		return super.put(item, id, timeout, not_item)
		
	def cycle_put_nowait(self, item, id=None, not_item=False):
		if id: return super.put_nowait(item, id, not_item)
		_id = self._thread_dict.next()
		id = _id if _id != self._id else self._thread_dict.next()
		return super.put_nowait(item, id, not_item)
		
	def cycle_get(self, bypass=True, timeout=None):
		timeout_initial = time.time()
		while self.ret_id != self.id():
			time.sleep(self.cycle_sleep)
			if timeout:
				if time.time() - timeout_initial > timeout:
					raise _queue.Empty
		if timeout:
			timeout = timeout - (time.time() - timeout_initial)
		_id = self._thread_dict.next(1)
		self.ret_id = _id if _id != self._id else self._thread_dict.next(1)
		return super().get(bypass, timeout)
	
	def cycle_get_nowait(self, bypass=True):
		timeout_initial = time.time()
		if self.ret_id != self.id():
			raise _queue.Empty
		_id = self._thread_dict.next(1)
		self.ret_id = _id if _id != self._id else self._thread_dict.next(1)
		return super().get(bypass, timeout)
	
	def assign(self, id="__NONE__"):
		if id == "__NONE__": id = uuid.uuid1().int
		super().assign(id)
		_id = self._thread_dict.retrieve(0)
		self.ret_id = _id if _id != self._id else self._thread_dict.retrieve(1)
		
Empty = _queue.Empty