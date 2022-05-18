import os

from send_code_main import *
from send_code_send import *
from send_code_recv import *
from send_code_message import *
from utils import *

import fs
import oscli
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
	if a == 2 or a == 4:
		do_fsc_run(filename, a, x, y)
	elif a == 3:
		do_fsc_oscli(filename, a, x, y)
	elif a == 5:
		do_fsc_cat(filename, a, x, y)
	else:
		# Unsupported - go to resting state with unchanged regs
		send_code_main(a, x, y)

# FSC functions 2 and 4 mean RUN
def do_fsc_run(filename, a, x, y):
	log(1, "    RUN %s" % filename)

	# Fetch the file content from storage
	content = None
	try:
		with fs.openfile(filename, "rb") as fp:
			content = fp.read()
			fp.close()
	except FileNotFoundError:
		send_code_main(a, x, y) # fixme: should give error?
		return

	hexdump(content)

	inf = fs.readinf(filename)

	# Tell the client to receive the content data
	send_code_recv(inf.addr_load, inf.length, content)

	# Return the client to resting state but transferring
	# execution to addr_exec rather than just returning to
	# the caller
	send_code_mainexec(a, x, y, inf.addr_exec)


# Unrecognized star command
def do_fsc_oscli(command, a, x, y):
	if not oscli.handle(command, a, x, y):
		do_fsc_run(command, a, x, y)


# CAT
def do_fsc_cat(filename, a, x, y):
	log(1, "    CAT %s" % filename)

	send_code_message("Directory: %s\r\n" % fs.getdir())

	# See what files we have
	filenames = sorted([fn for fn in fs.listdir(".")])

	files_in_dir = ["  "+f[2:] for f in filenames if fs.file_in_current_dir(f)]

	files_in_other_dirs = [f for f in filenames if not fs.file_in_current_dir(f)]
	
	for files in (files_in_dir, files_in_other_dirs):
		# Execute the catalogue handler for these files
		send_code_fromfile("data/catalogue.x", (3, len(files)))

		# Sort the filenames and send them one by one
		for f in sorted(files):

			# Wait for the client to be ready - as it reenables
			# interrupts and prints each filename as it goes, we
			# don't want to send more data until it is ready
			log(3, "    waiting...")
			while not ser.read(1):
				pass

			# Send the next filename, backwards
			log(3, "    sending %s" % f)
			ser.write(s2b(f[::-1]+"\0"))

		# Wait again at the end, it may not be ready for the next code yet
		while not ser.read(1):
			pass

	# Send the main code to return to resting state
	send_code_main(a, x, y)


