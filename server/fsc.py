import os

from send_code_main import *
from send_code_send import *
from send_code_recv import *
from utils import *

import osfile


# List of FSC functions that use X/Y to point to a filename
fscs_with_filename = set([2, 3, 4, 5])

# FSC
def do_fsc(a, x, y):
	log(2, "    OSFSC %02x  %02x %02x" % (a, x, y))

	# Fetch the filename now if there is one
	if a in fscs_with_filename:
		filename = send_code_sendstring(x+y*256, 16)
		filename = sanitize_filename(filename)

	# Dispatch subfunctions appropriately
	if a in (2, 3, 4):
		do_fsc_run(filename, a, x, y)
	elif a == 5:
		do_fsc_cat(filename, a, x, y)
	else:
		# Unsupported - go to resting state with unchanged regs
		send_code_main(a, x, y)

# FSC functions 2,3,4 all mean RUN
def do_fsc_run(filename, a, x, y):
	log(1, "    RUN %s" % filename)

	# Fetch the file content from storage
	content = None
	try:
		with open("storage/%s" % filename, "rb") as fp:
			content = fp.read()
			fp.close()
	except FileNotFoundError:
		send_code_main(a, x, y) # fixme: should give error?
		return

	hexdump(content)

	# The client doesn't need a parameter block but it's useful
	# here just for reading the inf file data
	param_block = [0]*0x12

	assert osfile.update_params_from_inf(param_block, filename)

	addr_load = read32(param_block, 2)
	addr_exec = read32(param_block, 6)
	length = read32(param_block, 10)

	# Tell the client to receive the content data
	send_code_recv(addr_load, length, content)

	# Return the client to resting state but transferring
	# execution to addr_exec rather than just returning to
	# the caller
	send_code_mainexec(a, x, y, addr_exec)


# CAT
def do_fsc_cat(filename, a, x, y):
	log(1, "    CAT %s" % filename)

	# See what files we have
	filenames = [fn for fn in os.listdir("storage") if len(fn)<16 and not fn.endswith(".inf")]
	
	# Execute the catalogue handler
	send_code_fromfile("data/catalogue.x", (3, len(filenames)))

	# Sort the filenames and send them one by one
	for f in sorted(filenames):

		# Wait for the client to be ready - as it reenables
		# interrupts and prints each filename as it goes, we
		# don't want to send more data until it is ready
		log(3, "    waiting...")
		while not ser.read(1):
			pass

		# Send the next filename, backwards
		log(3, "    sending %s" % f)
		ser.write(s2b(f[::-1]+"\0"))

	# Wait again at the end, it may not be ready for the code yet
	while not ser.read(1):
		pass

	# Send the main code to return to resting state
	send_code_main(a, x, y)


