import re

from send_code import *
from send_code_error import *
from send_code_main import *
from send_code_send import *
from send_code_recv import *

import fs

from utils import *

# Update an OSFILE parameter block from an inf file
def update_params_from_file(param_block, f):
	write32(param_block, 2, f.addr_load)
	write32(param_block, 6, f.addr_exec)
	write32(param_block, 10, f.length)
	write32(param_block, 14, f.attr)


# OSFILE handler
def do_file(a, x, y):
	log(2, "    OSFILE &%02x / %02x%02x" % (a, y, x))

	# All OSFILE calls use a parameter block, so first get
	# a copy of that and the filename it refers to
	send_code_fromfile("data/osfile.x", (3, a), (4, x), (5, y))

	param_block = list(ser.read(0x12))

	filename = read_filename()

	# Next actions depend on which OSFILE subcommand is chosen
	# by the A register
	handlers = {
		0xff: do_file_load,
		0x00: do_file_save,
		0x01: do_file_writeparams,
		0x02: do_file_writeload,
		0x03: do_file_writeexec,
		0x04: do_file_writeattr,
		0x05: do_file_readparams,
		0x06: do_file_delete
	}
	if a not in handlers:
		log(1, "    Unsupported OSFILE &%02x" % a)
		send_code_main(a, x, y)
	else:
		handlers[a](param_block, filename, a, x, y)


# OSFILE LOAD handler
def do_file_load(param_block, filename, a, x, y):
	# We might use this address, or might use an updated
	# address from the file's stored metadata
	addr_load = read32(param_block, 2)

	# Do we use the default address or the user-supplied one?
	default_address = (param_block[6] != 0)

	log(1, "    OSFILE LOAD %s %s" % (filename, "" if default_address else ("%04x" % addr_load)))

	# Fetch the content from storage
	f = fs.file(filename)
	if not f.exists:
		send_code_error_filenotfound()
		return

	content = f.read()

	hexdump(content)

	# Update the parameter block based on the inf file
	update_params_from_file(param_block, f)

	# If we're meant to use the file's default load address,
	# do so now
	if default_address:
		addr_load = read32(param_block, 2)

	length = read32(param_block, 10)

	# Tell the client to receive the content data
	send_code_recv(addr_load, length, content)
	# Tell the client to receive the new parameter block
	send_code_recv(x+256*y, 0x12, param_block)

	# Return the client to its resting state, with A=1
	# to indicate that a file was loaded
	send_code_main(1, x, y)


# OSFILE 1 - write all params
def do_file_writeparams(param_block, filename, a, x, y):
	log(1, "    OSFILE WRITEPARAMS %s" % filename)
	writeparams_helper(param_block, filename, True, True, True, a, x, y)

# OSFILE 2 - write load address
def do_file_writeload(param_block, filename, a, x, y):
	log(1, "    OSFILE WRITELOAD %s" % filename)
	writeparams_helper(param_block, filename, True, False, False, a, x, y)

# OSFILE 3 - write execution address
def do_file_writeexec(param_block, filename, a, x, y):
	log(1, "    OSFILE WRITEEXEC %s" % filename)
	writeparams_helper(param_block, filename, False, True, False, a, x, y)

# OSFILE 4 - write attributes
def do_file_writeattr(param_block, filename, a, x, y):
	log(1, "    OSFILE WRITEATTR %s" % filename)
	writeparams_helper(param_block, filename, False, False, True, a, x, y)

# Helper for writing some/all params for a file
def writeparams_helper(param_block, filename, writeload, writeexec, writeattr, a, x, y):
	f = fs.file(filename)
	if not f.exists:
		send_code_main(0, x, y)
		return

	if writeload:
		f.addr_load = read32(param_block, 2)
	if writeexec:
		f.addr_exec = read32(param_block, 6)
	if writeattr:
		f.attr = read32(param_block, 14)

	f.writeinf()

	if False:
		update_params_from_file(param_block, f)
	
		# ... and tell the client to receive it
		send_code_recv(x+256*y, 0x12, param_block)

	# Then go to resting state
	send_code_main(1, x, y)


# OSFILE 5 - read all params
def do_file_readparams(param_block, filename, a, x, y):
	log(1, "    OSFILE READPARAMS %s" % filename)

	f = fs.file(filename)
	if not f.exists:
		send_code_main(0, x, y)
		return

	update_params_from_file(param_block, f)

	# ... and tell the client to receive it
	send_code_recv(x+256*y, 0x12, param_block)

	# Then go to resting state
	send_code_main(1, x, y)


# OSFILE SAVE
def do_file_save(param_block, filename, a, x, y):
	addr_load = read32(param_block, 2)
	addr_exec = read32(param_block, 6)
	addr_start = read32(param_block, 10)
	addr_end = read32(param_block, 14)

	length = addr_end - addr_start

	log(1, "    OSFILE SAVE %s %04x %04x %04x %04x" % (
		filename,
		addr_start,
		addr_end,
		addr_exec,
		addr_load))

	# Tell client to send the data it wants to save
	content = send_code_send(addr_start, length)

	log(3, bytes(content))

	f = fs.file(filename)
	f.write(content)

	f.addr_load = addr_load
	f.addr_exec = addr_exec
	f.writeinf()

	# Update the parameter block as the field meanings are
	# different after a SAVE to what they are beforehand
	update_params_from_file(param_block, f)

	# Tell the client to receive the new parameter block
	send_code_recv(x+256*y, 0x12, param_block)

	# Put the client in resting state
	send_code_main(1, x, y)


# OSFILE 6 - delete
def do_file_delete(param_block, filename, a, x, y):
	log(1, "    OSFILE DELETE %s" % filename)
	
	f = fs.file(filename)
	if not f.exists:
		fs.closefile(h)
		send_code_main(0, x, y)
		return

	try:
		f.delete()
	except:
		send_code_error_filelocked()
		return

	send_code_main(a, x, y)

