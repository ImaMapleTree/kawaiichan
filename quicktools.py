import json
from os import path
import codecs
import traceback
from datetime import date
from collections import OrderedDict

def gen_date_name(dir="", ext=".txt"):
	today = date.today()
	name = today.strftime("%Y-%m-%d"); i = 1
	while path.isfile(os.path.join(dir, f"{name}-{i}{ext}")): i += 1
	return f"{name}-{i}{ext}"

def int_to_bytes(int, order="little"):
	if int == 0: return b"\00"
	if order == "small": order = "little"
	amount = (int.bit_length() + 7) // 8
	return int.to_bytes(amount, order)

def JOpen(location, mode, savee=None):
	if mode == 'r' or mode == 'r+':
		if path.exists(location) != True: return(None) #Checks if path exists, if not returns false.
		TOP = codecs.open(location, "r", "utf-8")
		quick_json = json.load(TOP)
		TOP.close()
		return(quick_json)
	elif mode == 'w' or mode == 'w+':
		with open(location, mode) as TOP:
			json.dump(savee, TOP, indent=3)
			TOP.close()
		return()

def SplitFind(string, term, term2=None, bump=1):
	pos1 = string.find(term) + bump
	if term2 == None:
		term2 = term
	pos2 = string.find(term2, pos1)
	field = string[pos1:pos2]
	return(field, pos1, pos2)
	
class TemporaryDict(dict):
	def __init__(self, limit=1, *args, **kwargs):
		super(TemporaryDict, self).__init__(*args, **kwargs)
		self.limit = limit
		if limit != 1:
			self.limit_dict = {}
		
	def __getitem__(self, key):
		print("I triggered")
		if key in self:
			if limit == 1:
				return self.pop(key)
			else:
				if key not in self.limit_dict: self.limit_dict[key] = 0
				if self.get(key) != None:
					self.limit_dict[key] += 1
					if self.limit_dict[key] >= self.limit:
						return self.pop(key)
					return self.get(key)
	
class redict(OrderedDict):
	def __init__(self, *args, **kwargs):
		super(redict, self).__init__(*args, **kwargs)
		
	def getKey(self, value, occur=0, localDict=None):
		occurence = -1
		if localDict == None: localDict = self
		for item in localDict.keys():
			if localDict[item] == value:
				occurence += 1
				if occurence == occur: return item
			if type(localDict[item]) == type({}):
				check = self.getKey(value, occur, localDict[item])
				if check: return check
		return None
		
class CommonKey():
	def __init__(self, *values):
		self.values = values
		self._softlimit = 50
	
	def asKey(self, static=True):
		pInt = 1
		hash_code = 0
		for val in self.values:
			hash_code += hash(val)*(pInt/self._softlimit)
			if static: pInt += 1
		return hash_code
	
class DictParser():
	def __init__(self, obj):
		self.rd = redict(obj)
		self.addresses = redict()
		self._ROUTE = []
		self._flatten()
	
	def fromAddress(self, address):
		keys = address.split("/")
		localDict = self.rd
		for key in keys:
			value = localDict.get(key)
			if value == None: return None
			if key == keys[-1]: return value
			if type(value) != type({}): continue
			localDict = value
	
	def toAddress(self, address, value, newDict="STDBY"):
		if newDict == "STDBY": newDict = self.rd
		keys = address.split("/")
		localDict = newDict
		for key in keys:
			CV = localDict.get(key)
			if CV == None: return
			if key == keys[-1]: localDict[key] = value
			if type(CV) != type({}): continue
			localDict = CV
			
	def copyformat(self, format):
		copied = redict(self.rd)
		for key in format.keys():
			value = self.fromAddress(key)
			fKey = format[key]
			try:
				if fKey == "int": self.toAddress(key, int(value), copied)
				elif fKey == "float": self.toAddress(key, float(value), copied)
			except: traceback.print_exc()
		return copied
			
	def _flatten(self, localDict=None):
		def joinroute(route, key):
			if route == []: return key
			return "/".join(self._ROUTE) + "/" + key
		
		if localDict == None: localDict = self.rd
		for key in localDict.keys():
			item = localDict[key]
			if type(item) == type({}): self._ROUTE.append(key); self._flatten(item)
			elif type(item) == type([]): pass
			else: self.addresses[joinroute(self._ROUTE, key)] = item
		if len(self._ROUTE) > 0: self._ROUTE.pop(len(self._ROUTE)-1)
		return