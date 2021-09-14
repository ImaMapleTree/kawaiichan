import json
from os import path
import pathlib
from quicktools import JOpen, DictParser
import glob

global SOURCE_CONFIG
global CFG_BASE
SOURCE_CONFIG = ""
CFG_BASE = ""


def set_source(source):
    global SOURCE_CONFIG
    SOURCE_CONFIG = read_raw(path.join(CFG_BASE, source))


def set_base_path(path):
    global CFG_BASE
    CFG_BASE = path


class CDMeta(type):
    pass


def shorten_source(source):
    filename = pathlib.Path(source)
    # i = source.rfind("\\")
    # if i == -1: return source
    # return source[i+1:].replace(".ecfg", "")
    return filename.name.replace(".ecfg", "")


def read_raw(source):
    with open(path.join(CFG_BASE, source), 'r') as f:
        txt = f.read()
    return txt


def writefile(source, info):
    with open(source, "w+") as f:
        f.write(info)
    return


class CabinetDict(dict, metaclass=CDMeta):
    def __init__(self, cabinet, auto_create=True, *args, **kwargs):
        super(CabinetDict, self).__init__(*args, **kwargs)
        self.cabinet = cabinet
        self.auto_create = auto_create

    def __getitem__(self, key):
        if not key in self:
            if self.auto_create:
                self[key] = None; self.cabinet.dump(self); print(f"Created entry for missing config-key ({key})")
            else:
                raise KeyError
        return super().get(key)

    def get(self, key, default=None):
        if not key in self:
            if self.auto_create:
                self[key] = default; self.cabinet.dump(self); print(f"Created entry for missing config-key ({key})")
            else:
                return default
        return super().get(key, default)

    def save(self):
        self.cabinet.dump()


class cabinet():
    def __init__(self, list, indent="\t", source=None, format=None):
        self.input_list = list
        self.final_object = CabinetDict(self)
        self._CSPACE = 0
        self._cachecfg = ""
        self.indent = indent
        self._furthest = 0
        self.source = source
        self.format = format
        self.ranked = False
        self.createFormat = False
        self.auto_create = True

    @classmethod
    def from_source(cls, source, indent="\t"):
        filename = path.splitext(source)[0]
        txtlist = read_raw(source).split("\n")
        formatting = JOpen(path.join(CFG_BASE, f"{filename}.ivf"), "r+")
        return cls(txtlist, indent, source, format=formatting)

    @classmethod
    def from_string(cls, string, indent="\t"):
        txtlist = string.split("\n")
        return cls(txtlist, indent)

    def from_object(cls, object, name, indent="\t"):
        cab = cls([], indent, f"{name}.ecfg")
        cab.final_object = object
        return cab

    def CSCheck(self, line):
        index = 0
        while True:
            if line[index:index + 1] != self.indent: return index
            index += 1

    def dump_format(self):
        if not self.ranked: print("[Error] Attempted to create a format file for a Cabinet that hasn't been ranked yet, if this is intentional you can ignore this message."); return
        if not self.source: return
        filename = path.splitext(self.source)[0]
        DP = DictParser(self.final_object)
        FDICT = dict(DP.addresses)
        for key in DP.addresses.keys():
            value = FDICT[key]
            if self.format:
                DV = self.format.get(key)
                if not DV and type(value) == type(""): FDICT.pop(key); continue
                if not DV:
                    FDICT[key] = type(value).__name__
                else:
                    FDICT[key] = DV
            else:
                if type(value) == type(""): FDICT.pop(key); continue
                FDICT[key] = type(value).__name__
        if self.format != FDICT: JOpen(path.join(CFG_BASE, f"{filename}.ivf"), "w+", FDICT)

    def dump(self, object=None, source=None):
        if not source: source = self.source
        if not self.ranked: print(
            "[Warning] Attempted to dump a Cabinet that hasn't been ranked yet, if this is intentional you can ignore this message.")

        def addSpace(space, indent):
            txtspace = ""
            for i in range(space):
                txtspace += indent
            return txtspace

        if object == None: self._CSPACE = 0; self._cachecfg = ""; object = self.final_object
        for key in object.keys():
            space = addSpace(self._CSPACE, self.indent)
            value = object.get(key)
            if type(value) == type({}):
                self._cachecfg += space + "{" + key + "}\n"; self._CSPACE += 1; self.dump(value)
            elif type(value) == type([]):
                self._cachecfg += space + "[" + key + "]\n"
                for thing in value: self._cachecfg += space + self.indent + thing + "\n"
            else:
                self._cachecfg += space + key + ": " + str(value) + "\n"
        self._CSPACE -= 1
        if object == self.final_object: writefile(source, self._cachecfg)
        return

    def rank(self, start_index=0, object=None):
        self.ranked = True

        def format(object, key, value):
            isList = bool(type(value) == type([]))
            isObjList = bool(type(key) == type([]))
            try:
                int(value); isInt = True
            except:
                isInt = False
            if isinstance(value, dict) and isObjList:
                object.append(value); return
            elif isinstance(value, dict):
                object[key] = value; return
            if type(object) == type([]) and isInt:
                object.append(int(value)); return
            elif type(object) == type([]):
                object.append(value); return
            elif not isList and value.lower() == "true":
                object[key] = True; return
            elif not isList and value.lower() == "false":
                object[key] = False; return
            elif not isList and not isObjList and isInt:
                object[key] = int(value); return
            if isinstance(value, list) or isinstance(value, dict): object[key] = value; return
            if value.find("|s") != -1:
                value = str(value.replace("|s", "")); self.createFormat = True
            elif value.find("|f") != -1:
                value = float(value.replace("|f", "")); self.createFormat = True
            else:
                object[key] = value

        if object == None: object = self.final_object
        index = 0
        next_list = []
        isObj = isinstance(object, dict)
        isList = isinstance(object, list)
        for line in self.input_list:
            if start_index < self._furthest:
                start_index = self._furthest
            elif start_index > self._furthest:
                self._furthest = start_index
            if index < start_index: index += 1; continue;
            if self.CSCheck(line) < self._CSPACE: self._CSPACE -= 1; break
            SKEY = line.find(": ")
            OKEY = line.find("{")
            LKEY = line.find("[")
            if isObj and SKEY != -1:
                key = line[:SKEY].replace("\t", "").replace("\r", ""); value = line[SKEY + 2:]; format(object, key,
                                                                                                       value)
            elif isObj and OKEY != -1:
                key = line[OKEY + 1:].replace("}", "").replace("\r", ""); value = {}; format(object, key,
                                                                                             value); self._CSPACE += 1; self.rank(
                    index + 1, object[key])
            elif isList and OKEY != -1:
                object.append({}); self._CSPACE += 1; self.rank(index + 1, object[len(object) - 1])
            elif isList and LKEY != -1:
                object.append([]); self._CSPACE += 1; self.rank(index + 1, object[len(object) - 1])
            elif isObj and LKEY != -1:
                key = line[LKEY + 1:].replace("]", "").replace("\r", ""); value = []; format(object, key,
                                                                                             value); self._CSPACE += 1; self.rank(
                    index + 1, object[key])
            elif type(object) == type([]):
                format(object, None, line[self._CSPACE:])
            index += 1
        if index > self._furthest: self._furthest = index
        if object == self.final_object:
            if self.createFormat: self.dump_format()
            if not self.format: return object
            DPC = DictParser(object)
            return DPC.copyformat(self.format)
        return object


def raw_load_all(dir=""):
    slashes = ["/", "\\"]
    if dir[len(dir) - 1] not in slashes: dir += "/"
    dir += "*.ecfg"
    load_list = glob.glob(dir)
    configs = {}
    for config in load_list:
        configs[shorten_source] = raw_load(config)
    return configs


def load_all(dir=""):
    slashes = ["/", "\\"]
    if dir[len(dir) - 1] not in slashes: dir += "/"
    dir += "*.ecfg"
    load_list = glob.glob(dir)
    configs = {}
    for config in load_list:
        configs[shorten_source(config)] = load(config)
    return configs


def raw_load(source="config.ecfg", indent="\t"):
    cab = cabinet.from_source(source, indent)
    return cab


def load(source="config.ecfg", indent="\t"):
    global SOURCE_CONFIG
    temp_path = path.join(CFG_BASE, source)
    if source == "config.ecfg" and not path.exists(temp_path):
        open(temp_path, "w+").write(SOURCE_CONFIG);
    elif not path.exists(temp_path):
        open(temp_path, "w+")
    cab = raw_load(source, indent)
    return cab.rank()
