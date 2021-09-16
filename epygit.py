import os
import sys
import getopt
import epycmd

args = sys.argv[1:]
try:
	opts, args =  getopt.getopt(args,"d:m:g:r:i:")
except getopt.GetoptError:
	sys.exit()

dir = os.getcwd()
message = "Script-Push"
git_url = None

ignore = []
remove = []
for opt, arg in opts:
	if opt == "-d":
		dir = arg
	if opt == "-m":
		message = arg
	if opt == "-g":
		git_url = arg
	if opt == "-r":
		remove = arg.split(",")
		ignore += remove
	if opt == "-i":
		ignore += arg.split(",")
		
CMD = epycmd.CMDBuilder()
CMD.cd(dir)
if not os.path.exists(os.path.join(dir, ".git")):
	CMD.raw('echo "" >> README.md')
	CMD.git('init')
	if not git_url: print("Project initialized, but GitHub project URL required to push to github. Please enter a project URL."); git_url = input()
	CMD.git("add README.md")
	CMD.git('commit -m "Initial Commit"')
	CMD.git('branch -M main')
	CMD.git("remote add origin " + git_url)
	CMD.git('push -u origin main')
	os.system(CMD.build())
	CMD = epycmd.CMDBuilder()
	CMD.cd(dir)
CMD.git('add -A')
for f in ignore: CMD.git(f'reset {f}')
for f in remove: CMD.git(f'rm --cached {f}')
CMD.git(f'commit -m "{message}" -a')
CMD.git('push --set-upstream origin main')
os.system(CMD.build())
