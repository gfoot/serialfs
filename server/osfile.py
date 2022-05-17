import re

from send_code import *
from send_code_error import *
from send_code_main import *
from send_code_send import *
from send_code_recv import *

from utils import *

# Regexp for parsing inf files.  This tolerates but 
# ignores additional fields.
infre = re.compile(r' *([^ ]+) +([0-9a-zA-Z]+) +([0-9a-zA-Z]+) +([0-9a-zA-Z]+)')

# Update an OSFILE parameter block from an inf file
def update_params_from_inf(param_block, filename):
	try:
		with open("storage/%s.inf" % filename, "r") as fp:
			line = fp.read()
			fp.close()
	except FileNotFoundError:
		return False
	
	m = infre.match(line)
	assert m

	fn, addr_load, addr_exec, length = m.groups()
	
	write32(param_block, 2, int(addr_load, base=16))
	write32(param_block, 6, int(addr_exec, base=16))
	write32(param_block, 10, int(length, base=16))
	write32(param_block, 14, 0x77)

	return True


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
		0x05: do_file_attr
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
	content = None
	try:
		with open("storage/%s" % filename, "rb") as fp:
			content = fp.read()
			fp.close()
	except FileNotFoundError:
		send_code_error(214, "File not found")
		return

	hexdump(content)

	# Update the parameter block based on the inf file
	assert update_params_from_inf(param_block, filename)

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


# OSFILE 5 - read all attributes
def do_file_attr(param_block, filename, a, x, y):
	log(1, "    OSFILE ATTR %s" % filename)

	# All we do here is update the parameter block from the
	# inf file...
	if not update_params_from_inf(param_block, filename):
		send_code_main(0, x, y)

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

	# Update the parameter block as the field meanings are
	# different after a SAVE to what they are beforehand
	write32(param_block, 10, length)
	write32(param_block, 14, 0x77) # access permissions

	hexdump(param_block)

	# Tell the client to receive the new parameter block
	send_code_recv(x+256*y, 0x12, param_block)

	# Put the client in resting state
	send_code_main(1, x, y)

	# Save the actual content data
	with open("storage/%s" % filename, "wb") as fp:
		fp.write(bytes(content))
		fp.close()

	# Save the inf file
	with open("storage/%s.inf" % filename, "w") as fp:
		fp.write("% 16s  %04x %04x %04x\n" % (filename, addr_load, addr_exec, length))
		fp.close()


