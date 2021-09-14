class CMDBuilder():
	def __init__(self):
		self.cmds = []
		
	def cd(self, path):
		self.cmds.append("cd /d " + path)
		
	def dir(self):
		self.cmds.append("dir")
		
	def git(self, args):
		self.cmds.append("git " + args)
		
	def raw(self, raw):
		self.cmds.append(raw)
		
	def build(self):
		txt =  "&&".join(self.cmds)
		print(txt)
		return txt