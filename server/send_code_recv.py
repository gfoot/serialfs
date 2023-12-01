from send_code import *
from utils import *

import settings


# Send code to tell the client to receive data from the 
# server.  There are two handlers for this, chosen based 
# on transfer length.
def send_code_recv(addr, length, data):

	log(3, "%08x %08x" % (addr, length))
	log(3, "%d %d" % (length, len(data)))

	if settings.allow_irq_during_recv:
		# Experimental support for servicing interrupts
		# during the transfer
		#
		# This slows the transfer down from about 7.5K/s
		# to about 5K/s
		#
		# See [interrupts.md] for more information

		blocksize = 32

		send_code_fromfile("data/recvblockwithirq.x",
			(3, addr & 0xff),
			(4, (addr>>8) & 0xff),
			(5, length & 0xff),
			(6, (length>>8) & 0xff),
			(7, blocksize))

		hexdump(data[:length])

		while not ser.read(1):
			pass

		current_hshk = get_hshk()

		for offset in range(0, length, blocksize):
			b = bytes(data[offset:offset+blocksize])
			while get_hshk() == current_hshk:
				pass
			ser.write(b)
			current_hshk = not current_hshk

	elif length <= 256:

		send_code_fromfile("data/recvblocksmall.x",
			(1, addr & 0xff),
			(3, (addr>>8) & 0xff),
			(5, length))

		hexdump(data[:length])

		while not ser.read(1):
			pass

		ser.write(reversed(data))

	else:

		send_code_fromfile("data/recvblock.x",
			(3, addr & 0xff),
			(4, (addr>>8) & 0xff),
			(5, length & 0xff),
			(6, (length>>8) & 0xff))

		hexdump(data[:length])

		while not ser.read(1):
			pass

		ser.write(data)


