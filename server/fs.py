import os
import re


root = "storage"
current_directory = "$"

validchars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ!$-_=+"

def getdir():
	return ":0."+current_directory

def setdir(d):
	global current_directory
	current_directory = d

def file_in_current_dir(f):
	return f.startswith(current_directory+".") or "." not in f

def fn(name):
	d = current_directory
	if '.' in name:
		d = name[0]
		name = name[2:]
		assert d != '.'
		assert '.' not in name

	if d != '$':
		name = d+"."+name

	return root + "/" + name

def openfile(name, mode):
	return open(fn(name), mode)

def listdir(name):
	directory = root
	for filename in os.listdir(directory):
		if len(filename) >= 16:
			continue
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
			
		yield d+'.'+filename

def delete(name):
	os.remove(fn(name))

def exists(name):
	return os.path.exists(fn(name))

re_drive = re.compile(r':([0-9]+)\.(.*)')

def split(path):

	drive = 0

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

	for f in sorted(listdir(".")):
		m = regex.match(f)
		print(f, m)
		if m:
			yield drive, f


# Regexp for parsing inf files.  This tolerates but 
# ignores additional fields.
infre = re.compile(r' *([^ ]+) +([0-9a-zA-Z]+) +([0-9a-zA-Z]+) +([0-9a-zA-Z]+)')


class File:
	def __init__(self, name):
		self.name = name
		self.osname = fn(name)
		self.infname = fn(name)+".inf"
		
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

