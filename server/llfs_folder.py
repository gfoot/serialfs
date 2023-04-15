# Folder-based low level filesystem

import os

from utils import *


root = "storage"


def mount(volume):
	path = root +  "/" + volume
	if "/../" in path:
		return None

	path = fixcase(path)
	if not path:
		return None

	if not os.path.isdir(path):
		return None

	return FolderLLFS(path)


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


def listmounts():
	return list(os.listdir(root))


class FolderLLFS:

	def __init__(self, path):
		self.path = path


	def title(self):
		return self.path[len(root)+1:]


	def listdir(self):
		directory = self.path
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


	def osfilename(self, name):

		if name.startswith("$."):
			name = name[2:]		

		return self.path + "/" + name


	def open(self, name):
		osname = self.osfilename(name)
		infname = self.osfilename(name)+".inf"

		return File(name, osname, infname)


	def unmount(self):
		pass
		

class File:
	def __init__(self, name, osname, infname):
		self.name = name
		self.osname = osname
		self.infname = infname

		log(3, "    Folder LLFS: file %s => %s + %s" % (name, osname, infname))
		
		self.checkexists()


	def checkexists(self):

		self.exists = os.path.exists(self.osname)

		self.addr_load = None
		self.addr_exec = None
		self.length = None
		self.attr = 0x77
		self.extrainf = ""

		if self.exists:
			if not self.readinf():
				self.addr_load = 0
				self.addr_exec = 0
				self.attr = 0x77
				self.length = os.path.getsize(self.osname)


	def readinf(self):
		try:
			with open(self.infname) as fp:
				line = fp.read()
				fp.close()
		except FileNotFoundError:
			return

		infdata = line.split()
		assert len(infdata) >= 1

		if len(infdata) == 1:
			infdata.append("0")
		if len(infdata) == 2:
			infdata.append(infdata[-1])
		if len(infdata) == 3:
			infdata.append("%x" % os.path.getsize(self.osname))
		if len(infdata) == 4:
			infdata.append("77")

		log(2, repr(infdata))
		fn, addr_load, addr_exec, length, attr = infdata[:5]

		if fn.upper() != self.name.upper():
			log(2, "Warning - name mismatch - %s vs %s" % (fn.upper(), self.name.upper()))

		self.addr_load = int(addr_load, base=16)
		self.addr_exec = int(addr_exec, base=16)
		self.length = int(length, base=16)
		self.attr = int(attr, base=16)

		self.extrainf = ' '.join(infdata[5:])

		return True


	def writeinf(self):
		with open(self.infname, "w") as fp:
			fp.write("%s  %04x %04x %04x %04x %s\n" % ((self.name+16*" ")[:16], self.addr_load, self.addr_exec, self.length, self.attr, self.extrainf))
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
		self.writeinf()


	def delete(self):
		os.remove(self.osname)
		os.remove(self.infname)

		self.checkexists()


	def create(self):
		self.addr_load = 0
		self.addr_exec = 0
		self.length = 0
		self.attr = 0x77
		self.write([])
		self.writeinf()

		self.checkexists()


