# SSD disc image low level filesystem

import os

from utils import *


root = "storage"


def mount(volume):
	log(1, "llfs_ssd mounting %s" % volume);

	path = root +  "/" + volume
	if "/../" in path:
		return None

	path = fixcase(path)
	log(1, "llfs_ssd fixed case to %s" % path);
	if not path:
		return None

	if not path.lower().endswith(".ssd"):
		return None

	if os.path.isdir(path):
		return None

	return SSDLLFS(path)


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
	return []#list(os.listdir(root))


class DFSFile:

	def __init__(self, dataE, dataF, data):
		
		self.name = ''.join([chr(x) for x in dataE[:7]]).strip()
		self.direc = chr(dataE[7]&0x7f)
		self.locked = dataE[7]&0x80 != 0
		self.loadaddr = dataF[0] + 256*dataF[1] + 65536*(3&(dataF[6]>>2))
		self.execaddr = dataF[2] + 256*dataF[3] + 65536*(3&(dataF[6]>>6))
		self.length = dataF[4] + 256 * dataF[5] + 65536*(3&(dataF[6]>>4))
		self.sector = dataF[7] + 256 * (3 & dataF[6])

		dE, dF = self.encode()
		assert dE == dataE and dF == dataF, "mismatch:\n  %s vs %s\n  %s vs %s" % (repr(dE), repr(dataE), repr(dF), repr(dataF))

		offset = self.sector*256
		self.content = bytes(data[offset:offset+self.length])


	def encode(self):

		paddedname = self.name + " " * (7-len(self.name))

		dataE = [ord(c) for c in paddedname]
		dataE.append(ord(self.direc) + (0x80 if self.locked else 0))

		dataF = [
			self.loadaddr & 0xff,
			(self.loadaddr >> 8) & 0xff,
			self.execaddr & 0xff,
			(self.execaddr >> 8) & 0xff,
			self.length & 0xff,
			(self.length >> 8) & 0xff,
			((self.execaddr & 0x30000) >> 10) + ((self.length & 0x30000) >> 12)
			  + ((self.loadaddr & 0x30000) >> 14) + ((self.sector & 0x300) >> 8),
			self.sector & 0xff
		]

		return bytes(dataE), bytes(dataF)


class DFSCatalog:

	def __init__(self, data, writecallback):
		self.writecallback = writecallback

		pageE = data[0:256]
		pageF = data[256:512]

		title = pageE[:8] + pageF[:4]
		title = title.split(b'\0')[0]
		self.title = ''.join([chr(x) for x in title])

		self.cyclenum = pageF[4]
		numfiles = pageF[5] // 8
		self.opt = (pageF[6] // 16) & 3
		self.sectors = pageF[7] + 256 * (pageF[6]&3)

		self.files = {}
		for i in range(numfiles):
			offset = (i+1)*8
			dataE = pageE[offset:offset+8]
			dataF = pageF[offset:offset+8]
			file = DFSFile(dataE, dataF, data)
			self.files[file.direc.upper() + '.' + file.name.upper()] = file

		newPageE,newPageF = self.encode()

		if pageE != newPageE:
			print("page E mismatch:")
			for i in range(256):
				if pageE[i] != newPageE[i]:
					break
			print("page E mismatch from byte %d:\n" % i)
			print(pageE[i:])
			print(newPageE[i:])

		if pageF != newPageF:
			print("page F mismatch:")
			for i in range(256):
				if pageF[i] != newPageF[i]:
					break
			print("page F mismatch from byte %d:\n" % i)
			print(pageF[i:])
			print(newPageF[i:])



	def encode(self):
		
		# Encode title and disc metadata
		paddedtitle = self.title + '\0' * (12 - len(self.title))
		pageE = [ord(c) for c in paddedtitle[:8]]
		pageF = [ord(c) for c in paddedtitle[8:12]]
		pageF.extend([
			self.cyclenum,
			len(self.files)*8,
			(self.opt<<4) + (self.sectors>>8),
			self.sectors & 0xff
		])

		pageE = bytes(pageE)
		pageF = bytes(pageF)

		# Add entries for files
		sortedfiles = sorted((-v.sector, v) for v in self.files.values())
		for s,f in sortedfiles:
			dataE, dataF = f.encode()
			pageE += dataE
			pageF += dataF

		# Pad to ends of sectors
		assert len(pageE) == len(pageF)
		assert len(pageE) <= 256
		
		if len(pageE) < 256:
			pageE = pageE + b'\0' * (256-len(pageE))
			pageF = pageF + b'\0' * (256-len(pageF))

		return pageE, pageF


	def write(self):

		# Allocate sectors
		sector = 2
		for name,file in sorted(self.files.items()):
			if file.length:
				file.sector = sector
				sector += (file.length + 255) // 256
			else:
				file.sector = 2

		# Encode catalog
		pageE, pageF = self.encode()
		data = pageE + pageF

		# Add file data
		sortedfiles = sorted((v.sector, v) for v in self.files.values())
		for s,f in sortedfiles:
			filedata = f.content
			remainder = len(f.content) & 255
			if remainder:
				filedata += bytes(256-remainder)

			assert len(data) == 256*f.sector, "data length mismatch: len is %d should be %d" % (len(data), 256*f.sector)
			data += filedata

		# Pad to full size of disc image
		if len(data) < 256*self.sectors:
			data += bytes(256*self.sectors - len(data))

		self.writecallback(data)


class SSDLLFS:

	def __init__(self, path):
		self.path = path

		self.fp = open(self.path, "r+b")

		self.readcatalog()


	def readcatalog(self):
		log(2, "Reading catalog")

		self.fp.seek(0)
		self.catalog = DFSCatalog(self.fp.read(), self.write)

		log(2, "Title: %s" % self.catalog.title)


	def title(self):
		return self.catalog.title


	def listdir(self):
		for file in self.catalog.files.values():
			yield file.direc + '.' + file.name


	def open(self, name):
		return File(name, self.catalog)


	def write(self, data):
		self.fp.seek(0)
		self.fp.write(data)


	def unmount(self):
		self.fp.close()
		

class File:
	def __init__(self, name, catalog):
		self.name = name
		self.catalog = catalog

		self.checkexists()


	def checkexists(self):

		self.exists = self.name.upper() in self.catalog.files

		self.catent = None

		self.addr_load = None
		self.addr_exec = None
		self.length = None
		self.attr = 0x77
		self.extrainf = ""

		if self.exists:
			self.catent = self.catalog.files[self.name.upper()]

			self.addr_load = self.catent.loadaddr
			self.addr_exec = self.catent.execaddr
			self.length = self.catent.length
			self.attr = 0x77 if not self.catent.locked else 0



	def writeinf(self):
		self.catent.loadaddr = self.addr_load
		self.catent.execaddr = self.addr_exec
		self.catent.length = self.length
		self.catent.locked = (self.attr != 0x77)

		self.catalog.write()


	def read(self):
		return self.catent.content


	def write(self, content):
		self.catent.content = content
		self.length = len(content)
		self.writeinf()


	def delete(self):
		self.catalog.delete(self.name)

		self.checkexists()


	def create(self):
		self.addr_load = 0
		self.addr_exec = 0
		self.length = 0
		self.attr = 0x77
		self.write([])
		self.writeinf()

		self.checkexists()


