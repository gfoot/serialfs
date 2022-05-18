from send_code_main import *
from send_code_recv import *
from send_code_send import *
from utils import *

import fs

# OSGBPB
def do_gbpb(a, x, y):
	log(1, "    OSGBPB &%02x &%04x" % (a, x+y*256))

	param_block = send_code_send(x+y*256, 13)

	if a == 8:
		do_gbpb_readcurrentdirentries(param_block, a, x, y)
		return

	send_code_main(a, x, y)


def do_gbpb_readcurrentdirentries(param_block, a, x, y):
	log(2, "        read current directory entries")

	first = read32(param_block, 9)
	count = read32(param_block, 5)

	filenames_block = []

	index = -1
	for f in sorted(fs.listdir(fs.current_drive)):
		if not f.startswith(fs.current_directory + "."):
			continue

		f = f[2:]
		
		index += 1

		if index < first:
			continue
	
		filenames_block.append(len(f))
		for c in f:
			filenames_block.append(ord(c))

		count -= 1
		if count == 0:
			break

	
	send_code_recv(read32(param_block, 1), len(filenames_block), filenames_block)

	write32(param_block, 1, read32(param_block, 1) + len(filenames_block))
	write32(param_block, 5, count)
	write32(param_block, 9, index+1)
	send_code_recv(x+y*256, 13, param_block)

	send_code_main(a, x, y, sec=(count>0))

