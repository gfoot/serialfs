import re

from utils import *

import llfs_folder


filesystems = [ llfs_folder ]


current_directory = "$"
library = ":0.$"
current_drive = 0

mounts = []
initialized = False


validchars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ!$-_=+"


def initmounts():
	global initialized
	initialized = True
	mount(0, "DEFAULT")


def getdir(drive=-1):
	if drive == -1:
		drive = current_drive
	return ":%d.%s" % (drive, current_directory)

def setdir(d):
	global current_directory
	current_directory = d


def getllfs(drive=-1):
	if not initialized:
		initmounts()

	if drive == -1:
		drive = current_drive

	if drive < 0 or drive >= len(mounts):
		return None

	return mounts[drive]


def validdrive(drive):
	return getllfs(drive) != None


def gettitle(drive=-1):
	llfs = getllfs(drive)
	if not llfs:
		return ""

	return llfs.title()


def mount(drive, path):
	if drive < 0 or drive > 9:
		return False

	llfs = None

	for fs in filesystems:
		llfs = fs.mount(path)
		if llfs:
			break

	if not llfs:
		return False
	
	if drive >= len(mounts):
		mounts.extend([None] * (drive + 1 - len(mounts)))

	if mounts[drive]:
		mounts[drive].unmount()
		mounts[drive] = None

	mounts[drive] = llfs
	return True


def listmounts():
	m = []
	for fs in filesystems:
		m.extend(fs.listmounts())
	return m


def drive(drive):
	llfs = getllfs(drive)
	if not llfs:
		return False

	global current_drive
	current_drive = drive
	return True


def listdir(drive=-1):
	llfs = getllfs(drive)
	if llfs:
		for filename in llfs.listdir():
			yield filename



def file_in_current_dir(f):
	return f.startswith(current_directory+".") or "." not in f


re_drive = re.compile(r':([0-9]+)\.(.*)')

def split(path):

	drive = current_drive

	path = path.strip()

	if path.startswith('"') and path.endswith('"'):
		path = path[1:-1]

	m = re_drive.match(path)
	if m:
		drive = int(m.group(1))
		path = m.group(2)

	d = current_directory
	if '.' in path:
		d = path[0]
		path = path[2:]
		assert d != '.'
		assert '.' not in path

	return drive, d+"."+path
		

def glob(afsp):
	drive, afsp = split(afsp)
	log(3, "            glob: :%d %s" % (drive, afsp))
	
	regex = afsp.replace('$','\\$').replace('.', '\\.').replace('#','[^.]').replace('*','[^.]*')
	regex = re.compile('^'+regex+'$')

	for f in sorted(listdir(drive)):
		m = regex.match(f)
		if m:
			log(3, "            glob: :%d %s" % (drive, afsp))
			yield drive, f


# Regexp for parsing inf files.  This tolerates but 
# ignores additional fields.
infre = re.compile(r' *([^ ]+) +([0-9a-zA-Z]+) +([0-9a-zA-Z]+) +([0-9a-zA-Z]+)')



handles = [None]


# Lowish level file access - doesn't allocate a Beeb OS handle, etc
def file(filename):
	drive, name = split(filename)

	d = current_directory
	if '.' in name:
		assert name[1] == '.'
		d = name[0]
		name = name[2:]
		assert d != '.'
		assert '.' not in name

	name = d+"."+name


	llfs = getllfs(drive)
	if not llfs:
		return None

	return llfs.open(name)


# Higher level file access - open a file, allocate OS handle, create/truncate, etc
def openfile(filename, allow_read, allow_write):
	f = file(filename)
	if not f:
		return 0

	f.open(allow_read, allow_write)

	handle = None
	for i,filedata in enumerate(handles):
		if i and not filedata:
			handle = i

	if handle is None:
		handle = len(handles)
		handles.append(None)

	handles[handle] = f

	return handle


def closefile(handle):
	if handle < 1 or handle >= len(handles):
		return False
	
	if handles[handle]:
		handles[handle].close()
		handles[handle] = None
	
	return True


def closeall():
	for i in range(len(handles)):
		if handles[i]:
			closefile(i)
	return True


def flushall():
	for i in range(len(handles)):
		if handles[i]:
			handles[i].flush()


def getfile(handle):
	if handle >= 1 and handle < len(handles):
		return handles[handle]

def bput(handle, value):
	file = getfile(handle)

	if not file:
		return False

	file.bput(value)


def bget(handle):
	file = getfile(handle)

	if not file:
		return None

	return file.bget()

