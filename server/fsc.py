import os

from send_code_main import *
from send_code_send import *
from send_code_recv import *
from send_code_message import *
from send_code_error import *
from utils import *

import fs
import osargs
import oscli
import osfile


# Extract the first word from a command string and also
# return the index to the next non-space character for
# OSARGS 1 to use later on
def split_first_word(command):
	startindex = 0
	while startindex < len(command) and command[startindex] == " ":
		startindex += 1

	endindex = startindex
	while endindex < len(command) and command[endindex] != " ":
		endindex += 1

	nextindex = endindex
	while nextindex < len(command) and command[nextindex] == " ":
		nextindex += 1

	return command[startindex:endindex], nextindex


# List of FSC functions that use X/Y to point to a string
fscs_with_string = set([2, 3, 4, 5])

# FSC
def do_fsc(a, x, y):
	log(2, "    OSFSC %02x  %02x %02x" % (a, x, y))

	# Fetch the string now if there is one
	if a in fscs_with_string:
		command = send_code_sendstring(x+y*256, 255)
		filename, tailoffset = split_first_word(command)

	# Dispatch subfunctions appropriately
	if a == 1:
		do_fsc_ext(a, x, y)
	elif a == 2 or a == 4:
		do_fsc_run(filename, tailoffset, a, x, y)
	elif a == 3:
		do_fsc_oscli(command, filename, tailoffset, a, x, y)
	elif a == 5:
		do_fsc_cat(filename, a, x, y)
	else:
		# Unsupported - go to resting state with unchanged regs
		send_code_main(a, x, y)


# Helper to *RUN an executable
def run_worker(filename, tailoffset, a, x, y):
	f = fs.File(filename)
	if not f.exists:
		return False

	log(2, "        running %s" % filename)

	content = f.read()

	hexdump(content)

	osargs.set_tail_ptr(tailoffset+x+y*256)

	# Tell the client to receive the content data
	send_code_recv(f.addr_load, f.length, content)

	# Return the client to resting state but transferring
	# execution to addr_exec rather than just returning to
	# the caller
	send_code_mainexec(a, x, y, f.addr_exec)

	return True


# FSC function 1 - EXT#
def do_fsc_ext(a, x, y):
	log(1, "    EXT %d" % x)

	f = fs.checkhandle(x)
	if not f:
		send_code_error_channel()
		return

	x = 0xff if f.eof() else 0

	send_code_main(a, x, y)


# FSC functions 2 and 4 mean RUN
def do_fsc_run(filename, tailoffset, a, x, y):
	log(1, "    RUN %s" % filename)

	if not run_worker(filename, tailoffset, a, x, y):
		send_code_error_filenotfound()


# Unrecognized star command
def do_fsc_oscli(command, filename, tailoffset, a, x, y):
	log(1, "    *%s" % command)
	if oscli.handle(command, a, x, y):
		return

	if run_worker(filename, tailoffset, a, x, y):
		return

	if run_worker(fs.library+"."+filename, tailoffset, a, x, y):
		return

	send_code_error_badcommand()


# CAT
def do_fsc_cat(filename, a, x, y):
	log(1, "    CAT %s" % filename)
	
	drive = fs.current_drive
	if filename:
		try:
			drive = int(filename)
		except:
			send_code_error(205, "Bad drive")
			return

	if not fs.validdrive(drive):
		send_code_error(205, "Bad drive")
		return

	send_code_message("%s\r\n" % fs.gettitle(drive))
	send_code_message("Directory %s\r\n" % fs.getdir(drive))

	# See what files we have
	filenames = sorted([fn for fn in fs.listdir(drive)])

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


