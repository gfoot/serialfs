from connection import ser

import settings


# iso-8859-1 should allow all 256 base values to work in 
# strings as well as byte arrays
def s2b(s):
	return bytes(s, "iso-8859-1")

def log(level, *args):
	if level <= settings.loglevel:
		print(*args)


# Read a 16-bit value from a memory block
def read16(block, offset):
	return block[offset] + block[offset+1]*256

# Read a 32-bit value from a memory block
def read32(block, offset):
	return read16(block, offset) + 65536*read16(block, offset+2)

# Write a 16-bit value to a memory block
def write16(block, offset, value):
	block[offset] = value & 0xff
	block[offset+1] = (value >> 8) & 0xff

# Write a 32-bit value to a memory block
def write32(block, offset, value):
	write16(block, offset, value & 0xffff)
	write16(block, offset+2, (value >> 16) & 0xffff)


# Helper to receive a filename over the wire, terminated by
# any control character
def read_filename():
	filename = ""
	while True:
		x = ser.read(1)
		if x:
			if x[0] < 33:
				break
			filename += chr(x[0])

	return sanitize_filename(filename)


# Remove any leading/trailing whitespace and quotations
# from a filename, convert to upper case, and maybe some
# other things
def sanitize_filename(filename):
	filename = filename.strip()

	if filename.startswith('"') and filename.endswith('"'):
		filename = filename[1:-1]

	filename = filename.strip()

	filename = filename.replace('/', '')

	filename = filename.upper()

	return filename


# Print a hex dump of a data block for debugging
def hexdump(bb):
	for i in range(0, len(bb), 8):
		s = "%04x: " % i
		t = ""
		for j in range(8):
			ij = i+j
			s += ("%02x " % bb[ij]) if ij < len(bb) else "   "
			t += " " if ij >= len(bb) else "." if bb[ij] < 32 or bb[ij] > 126 else chr(bb[ij])

		log(3, "  ",s,t)


# Get's the handshake status, whether it's CTS or DSR
def get_hshk():
	if settings.handshake == "cts":
		return ser.cts
	else:
		return ser.dsr

