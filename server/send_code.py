from connection import ser
from utils import *

import settings


# Send some code for the client to execute, assuming it's 
# expecting it
def send_code(code, debuginfo=""):
	log(2, "Sending code%s" % ("" if not debuginfo else ": %s" % debuginfo))

	assert len(code) <= settings.max_code_size, "Code '%s' is too large (%d bytes > %d bytes)" % (filename, len(code), settings.max_code_size)

	log(3, "    send_code: waiting for client")
	while not ser.read(1):
		pass

	log(3, "    send_code: sending")
	hexdump(code)
	ser.write(bytes([len(code)]))
	ser.write(reversed(code))

# Send continuation code that just loads the registers and 
# returns to the caller already on the stack.  This is OK
# so long as the CLI handler hasn't already been overwritten.
def send_code_loadregs(a, x, y):
	code = [ 0xa9, a, 0xa2, x, 0xa0, y, 0x60 ]
	send_code(code, "loadregs")

# Send a specific file of compiled continuation code, first 
# applying a list of patches to e.g. apply register values
# or set up other data within the code
def send_code_fromfile(filename, *patches):
	with open(filename, "rb") as fp:
		code = list(fp.read())
		fp.close()

	for addr,value in patches:
		code[addr] = value

	send_code(bytes(code), filename)


