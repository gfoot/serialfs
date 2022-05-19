import os
import re


root = "storage"
current_directory = "$"
library = ":0.$"
current_drive = 0

mounts = [ "DEFAULT" ]

validchars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ!$-_=+"

def getdir(drive=-1):
	if drive == -1:
		drive = current_drive
	return ":%d.%s" % (drive, current_directory)

def setdir(d):
	global current_directory
	current_directory = d

def gettitle(drive=-1):
	if drive == -1:
		drive = current_drive
	if drive >= 0 and drive < len(mounts):
		return mounts[drive]
	return ""

# Do a case-insensitive search and adjust the filename's
# case if necessary
def fixcase(path):
	if os.path.exists(path):
		return path

	segments = path.split('/')
	for i in range(len(segments)):
		direc = '/'.join(segments[:i])
		if not direc:
			direc = "."
		if not os.path.isdir(direc):
			return None
		if os.path.exists(direc+"/"+segments[i]):
			continue

		for entry in os.listdir(direc):
			if entry.upper() == segments[i].upper():
				segments[i] = entry
				break

	return '/'.join(segments)


def mount(drive, relpath):
	path = root + "/" + relpath
	if "/../" in path:
		return False
	path = fixcase(path)
	if not path:
		return False
	if not os.path.isdir(path):
		return False
	if drive < 0:
		return False
	
	if drive >= len(mounts):
		mounts.extend([None] * (drive + 1 - len(mounts)))

	mounts[drive] = path[len(root)+1:]
	return True

def listmounts():
	return list(os.listdir(root))

def drive(drive):
	if not validdrive(drive):
		return False

	global current_drive
	current_drive = drive
	return True


def file_in_current_dir(f):
	return f.startswith(current_directory+".") or "." not in f

def fn(drive, name):
	
	d = current_directory
	if '.' in name:
		d = name[0]
		name = name[2:]
		assert d != '.'
		assert '.' not in name

	if d != '$':
		name = d+"."+name

	return root + "/" + mounts[drive] + "/" + name

def validdrive(drive):
	return drive >=0 and drive < len(mounts) and mounts[drive]

def listdir(drive=-1):
	if drive == -1:
		drive = current_drive
	
	if not validdrive(drive):
		return

	directory = root + "/" + mounts[drive]
	for filename in os.listdir(directory):
		if filename.endswith(".inf"):
			continue
		if os.path.isdir(directory + "/" + filename):
			continue
		d = '$'
		if '.' in filename:
			d = filename[0]
			filename = filename[2:]
			if d == '.' or '.' in filename:
				continue
		
		result = d+'.'+filename
		if len(result) >= 18:
			continue

		yield result


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
	print(drive, afsp)
	
	regex = afsp.replace('$','\\$').replace('.', '\\.').replace('#','[^.]').replace('*','[^.]*')
	print(regex)
	regex = re.compile('^'+regex+'$')

	for f in sorted(listdir(drive)):
		m = regex.match(f)
		print(f, m)
		if m:
			yield drive, f


# Regexp for parsing inf files.  This tolerates but 
# ignores additional fields.
infre = re.compile(r' *([^ ]+) +([0-9a-zA-Z]+) +([0-9a-zA-Z]+) +([0-9a-zA-Z]+)')


class File:
	def __init__(self, name):
		drive, name = split(name)

		self.drive = drive
		self.name = name
		self.osname = fn(self.drive, name)
		self.infname = fn(self.drive, name)+".inf"
		
		self.exists = os.path.exists(self.osname)

		self.addr_load = None
		self.addr_exec = None
		self.length = None

		if self.exists:
			if not self.readinf():
				self.addr_load = 0
				self.addr_exec = 0
				self.length = os.path.getsize(self.osname)


	def readinf(self):
		try:
			with open(self.infname) as fp:
				line = fp.read()
				fp.close()
		except FileNotFoundError:
			return

		m = infre.match(line)
		assert m
		if not m:
			return None

		fn, addr_load, addr_exec, length = m.groups()
		if fn.upper() != self.name.upper():
			print("Warning - name mismatch - %s vs %s" % (fn.upper(), self.name.upper()))

		self.addr_load = int(addr_load, base=16)
		self.addr_exec = int(addr_exec, base=16)
		self.length = int(length, base=16)

		return True


	def writeinf(self):
		with open(self.infname, "w") as fp:
			fp.write("%s  %04x %04x %04x\n" % ((self.name+16*" ")[:16], self.addr_load, self.addr_exec, self.length))
			fp.close()


	def read(self):
		with open(self.osname, "rb") as fp:
			content = fp.read()
			fp.close()
		return content


	def write(self, content):
		with open(self.osname, "wb") as fp:
			fp.write(bytes(content))
			fp.close()
		self.length = len(content)

	def delete(self):
		os.remove(self.osname)
		os.remove(self.infname)


	def open(self, allow_read, allow_write):
		self.allow_read = allow_read
		self.allow_write = allow_write
	
		if self.allow_write and not self.allow_read:
			if self.exists:
				self.delete()
				self.exists = False

		if not self.exists:
			if not self.allow_write:
				return False

			self.addr_load = 0
			self.addr_exec = 0
			self.length = 0
			self.write([])
			self.writeinf()

		self.content = list(self.read())
		self.length = len(self.content)
		self.pos = 0

		return True


	def close(self):
		assert self.content is not None

		self.flush()

		self.content = None

	
	def eof(self):
		return self.pos == len(self.content)


	def bput(self, value):
		if self.pos == len(self.content):
			self.content.append(value)
			self.length = len(self.content)
		else:
			self.content[self.pos] = value

		self.pos = self.pos + 1


	def bget(self):
		if self.eof():
			return None

		value = self.content[self.pos]
		self.pos = self.pos+1
		return value

	def seek(self, pos):
		if pos < 0 or pos > len(self.content):
			return False

		self.pos = pos
		return True

	def flush(self):
		if self.content and self.allow_write:
			self.write(self.content)
			self.writeinf()


handles = [None]


def openfile(filename, allow_read, allow_write):
	f = File(filename)
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


def checkhandle(handle):
	if handle >= 1 and handle < len(handles):
		return handles[handle]

def bput(handle, value):
	if not checkhandle(handle):
		return False

	handles[handle].bput(value)

def bget(handle):
	if not checkhandle(handle):
		return None

	return handles[handle].bget()

