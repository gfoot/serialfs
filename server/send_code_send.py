from send_code import *
from utils import *


# Send code to tell the client to send data back to the 
# server.
def send_code_send(addr, length):
	send_code_fromfile("data/sendblock.x",
		(3, addr & 0xff),
		(4, (addr >> 8) & 0xff),
		(5, length & 0xff),
		(6, (length >> 8) & 0xff))

	content = []
	while len(content) < length:
		content.extend(ser.read(length - len(content)))

	return content

# Send code to tell the client to send a string to the server.
# This is for cases where the server doesn't know the length
# in advance, so the usual send routine can't be used.  There
# is a maximum length in case the string is corrupted and not 
# terminated.
def send_code_sendstring(addr, maxlength):
	s = ""
	for b in send_code_send(addr, maxlength):
		if b == 13:
			 break
		s = s + chr(b)
	return s

