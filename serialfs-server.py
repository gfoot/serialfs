# Serial filing system server program
# 
# Listens for connections
# Sends initialization code
# Waits for commands
# Sends new code as required to execute commands
#
# Saved files are stored in the "storage" directory, along with
# 'inf' metadata files in what I believe is the standard format
# according to mdfs.net

import os
import re
import serial
import subprocess
import sys
import time


# Actually defined in init.s, but used here to check overlays
# are not too big.
himem = 0x9c


loglevel = 1

def log(level, *args):
	if level <= loglevel:
		print(*args)


# iso-8859-1 should allow all 256 base values to work in 
# strings as well as byte arrays
def s2b(s):
	return bytes(s, "iso-8859-1")


# Helper for sending simple commands for the client to execute
# during early initialization, when it's just normal serial
# text comms
def exec(s):
	log(3, " exec: %s" % s)
	ser.write(s2b(s+'\r'))


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


# Send some code for the client to execute, assuming it's 
# expecting it
def send_code(code, debuginfo=""):
	log(2, "Sending code%s" % ("" if not debuginfo else ": %s" % debuginfo))

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

	assert len(code) <= himem, "Code from %s is too large (%d bytes)" % (filename, len(code))

	send_code(bytes(code), filename)


# Send the "main" code, which restores the system to the
# default state ready for more CLI and filing system commands.
# This isn't quite the same state as after initialization but
# is close enough.
def send_code_main(a, x, y):
	send_code_fromfile("data/main.x", (3, a), (4, x), (5, y))

# Send the "main" code but instead of returning to the caller,
# jump to some other address (e.g. for *RUN)
def send_code_mainexec(a, x, y, addr):
	send_code_fromfile("data/main.x", 
		(3, a), (4, x), (5, y),
		(6, 0xff),
		(7, addr & 0xff), (8, (addr>>8) & 0xff))

# Send code to tell the client to receive data from the 
# server.  There are two handlers for this, chosen based 
# on transfer length.
def send_code_recv(addr, length, data):

	if length <= 256:

		send_code_fromfile("data/recvblocksmall.x",
			(1, addr & 0xff),
			(3, (addr>>8) & 0xff),
			(5, length))

		while not ser.read(1):
			pass

		ser.write(reversed(data))

	else:

		blocksize = 32

		send_code_fromfile("data/recvblock.x",
			(3, addr & 0xff),
			(4, (addr>>8) & 0xff),
			(5, length & 0xff),
			(6, (length>>8) & 0xff),
			(7, blocksize))

		while not ser.read(1):
			pass

		current_dsr = ser.dsr

		for offset in range(0, length, blocksize):
			b = bytes(data[offset:offset+blocksize])
			while ser.dsr == current_dsr:#read(1):
				pass
			ser.write(b)
			current_dsr = not current_dsr
			

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

# Send code to cause the client to print a message which is 
# embedded in the code
def send_code_printmessage(message):
	with open("data/message.x", "rb") as fp:
		code = list(fp.read())
		fp.close()

	codelen = len(code)
	capacity = himem - len(code)
	for pos in range(0, len(message), capacity):
		submessage = message[pos:pos+capacity]
		code[1] = len(submessage)
		code[codelen:] = s2b(submessage[::-1])

		assert len(code) <= himem, "Code with message is too large (%d bytes)" % (filename, len(code))

		send_code(bytes(code), "message")

# Send code to cause a BRK error on the client
def send_code_error(errno, message):
	with open("data/error.x", "rb") as fp:
		code = list(fp.read())
		fp.close()

	code.append(errno)
	code.extend(s2b(message))
	code.append(0)

	assert len(code) <= himem, "Code with error message is too large (%d bytes)" % (filename, len(code))

	send_code(bytes(code), "error")


# Bootstrap the client.  On entry the client is ready for
# BASIC commands, and output is disabled, so none of this
# is seen by the user.
# 
# We first run a BASIC command to build up a string variable
# byte by byte containing the machine code.
#
# Then in a second compound command we turn off normal serial 
# I/O (leaving input enabled but the input buffer disabled, 
# so that RTS is kept active), re-enable VDU output, write 
# the code into memory, and execute the init routine.
#
# The init routine installs the CLI handler and waits until
# the *S command is executed before doing anything further.
def send_init_program():

	log(1, "Sending init code")

	with open("data/init.x", "rb") as fp:
		code = fp.read()
		fp.close()

	# The last couple of bytes are used to indicate the target
	# load address for this code, usually A00 (the RS423 input
	# buffer) but it can be set differently to help debugging.
	addr = code[-2]+256*code[-1]

	# Strip those last bytes off as we need the total length 
	# to be no more than 255, otherwise it won't fit in a 
	# BASIC string
	code = code[:-2]

	# Check it's not too big
	num = len(code)
	if num > 255:
		print("Code too large (%d > %d)" % (num, 255))
		exec(':'.join([
			'OSCLI("FX3,0")',    # Output to VDU
			'OSCLI("FX2,0")',    # Input from keyboard only
			'P."Code too large, aborting"'
		]))
		return

	# Clear A$ and then read the init code into it one byte
	# at a time
	exec('A$=""')
	exec("FOR I%%=0 TO %d:A$=A$+GET$:N." % (num-1))
	ser.write(code)

	# There probably shouldn't be any output here unless it's
	# been enabled for debugging purposes
	printoutput()
	
	# Execute the final compound BASIC command to restore
	# TTY settings to long term values and install and
	# execute the init code
	exec(':'.join([
		'OSCLI("FX3,0")',    # Output to VDU
		'OSCLI("FX2,2")',    # Input from keyboard, RS423 active
		'OSCLI("FX204,1")',  # Disable RS423 input buffer
		'$&%X=A$' % addr,    # Write code to target address
		'CALL&%X' % addr     # Execute code
	]))

	# Wait for init program to start
	log(1, "Waiting...")
	while True:
		x = ser.read(1)
		if x == b'I':
			break
		if x:
			print("unexpected:",x)

	# Change rate to match settings sent to client above
	# (19200 baud with x4 multiplier)
	log(1, "Upgrading speed to 76800 baud")
	ser.baudrate = 76800

	# Send code to print startup message
	send_code_printmessage("\x0aSerialFS active\x0a\x0d")

	# Activate SerialFS
	send_code_fromfile("data/activate.x")

	# Send main code
	send_code_main(0, 0, 0)


# Receive a command from the client and send some continuation
# code to deal with it
#
# Commands are identified by a single byte, and sent along 
# with register contents as filing system APIs use the 
# registers to choose between functions
def do_command():
	a,x,y,cmd = ser.read(4)
	log(3, "Received command %02x, regs %02x %02x %02x" % (cmd, a, x, y))

	# The filing system command IDs are the low bytes of the
	# return address to whichever of our handlers was called
	# to process the command - this is the last byte of the
	# corresponding "jsr send_command" instruction, as noted
	# in src/init.s
	fsbase = 0xeb
	handlers = {
		fsbase+0x00: do_file,
		fsbase+0x03: do_args,
		fsbase+0x06: do_bget,
		fsbase+0x09: do_bput,
		fsbase+0x0c: do_gbpb,
		fsbase+0x0f: do_find,
		fsbase+0x12: do_fsc,

		# These are explicitly-chosen command IDs
		ord('*'): do_activate,
		ord('M'): do_main
	}

	if cmd not in handlers:
		print("Invalid command code")
		send_code_error(224, "SerialFS: Invalid command code")
		return

	# Chain to the appropriate handler
	handlers[cmd](a, x, y)


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


# OSARGS
def do_args(a, x, y):
	log(1, "    OSARGS")
	send_code_main(a, x, y)

# BGET
def do_bget(a, x, y):
	log(1, "    OSBGET")
	send_code_main(a, x, y)

# BPUT
def do_bput(a, x, y):
	log(1, "    OSBPUT")
	send_code_main(a, x, y)

# OSGBPB
def do_gbpb(a, x, y):
	log(1, "    OSGBPB")
	send_code_main(a, x, y)

# OSFIND
def do_find(a, x, y):
	log(1, "    OSFIND")
	send_code_main(a, x, y)


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

	assert update_params_from_inf(param_block, filename)

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


# Activation via *-command
def do_activate(a, x, y):
	log(1, "    *S (activate)")
	send_code_fromfile("data/activate.x")
	send_code_main(a, x, y)


# Client requested to be sent the main code
def do_main(a, x, y):
	log(1, "    M (main)")
	send_code_main(a, x, y)


# Read any pending output from the client, and print it
#
# This is only really useful during initialization, and then
# only if output has been enabled for debugging, as it's 
# usually turned off
def printoutput():
	if not ser.in_waiting:
		return

	x = ser.read(1)
	
	if x:
		while ser.in_waiting:
			x += ser.read(ser.in_waiting)

		s = x.decode("iso-8859-1")
		lines = [l+'\r' for l in s.split('\r')]
		lines[-1] = lines[-1][:-1]
		
		for line in lines:
			if line:
				log(3, repr(" R: "+line))


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


def assemble(inputfilename, outputfilename, labelfilename=None, impfilename=None):
	print("Assembling %s" % outputfilename)

	cmd = ["xa", inputfilename, "-o", outputfilename, "-M"]
	if labelfilename:
		cmd.extend(["-l", labelfilename])

	try:
		result = subprocess.run(cmd, check=True)
	except subprocess.CalledProcessError:
		print("\nAssembly of %s failed" % inputfilename)
		sys.exit(1)

	if labelfilename and impfilename:
		cmd = ["python", "genimports.py", labelfilename, impfilename]
		result = subprocess.run(cmd, check=True)


assemble("src/init.s", "data/init.x", "gen/init.labels", "gen/init.imp")

for f in os.listdir("src"):
	if f.endswith(".s") and f != "init.s":
		g = f[:-2]
		assemble("src/"+f, "data/"+g+".x")


# Default serial settings on the beeb seem to be 9600 8-N-1
#
# Experiments show this can easily be increased to 76800, with 
# 8-N-2 maybe being more reliable at that speed.  Receiving at
# higher speeds doesn't work because of the way the ACIA is 
# wired in the Beeb, but transmitting at higher speeds might 
# also be possible.  Not sure if Python Serial supports 
# asymmetric settings.
ser = serial.Serial("/dev/ttyUSB0", 9600, 8, "N", 1, timeout=1)


while True:

	# Reset to slow speed for initial connection
	ser.baudrate = 9600

	# Wait for a connection
	log(0, "")
	log(0, "Listening")
	while not ser.dsr:
		time.sleep(0.1)

	# The beeb is open for input now, but not output yet.
	# Wait until we see a prompt characte (">"), and 
	# occasionally send a command to enable serial output
	# until it appears.
	log(0, "Line open")
	attempts = 0
	while ser.dsr:
		if not ser.in_waiting:
			# Send the beeb a command to enable serial output.
			# *FX3,3 also disables VDU output, for tidiness.
			# While we send the command though, we cause the VDU
			# to erase each character so that it doesn't show up 
			# for the user.
			log(1, "Initializing link")

			# Printer off, clear input, erase prompt
			ser.write(b'\x03\x15\x08 \x7f')

			# Send a message to the VDU but erase it from the
			# input command buffer
			ser.write(b'\r\x08Initialising SerialFS...\x0a\x15')

			# Turn on serial output and turn off VDU output,
			# and hide the commands by erasing the characters
			s = ''.join([char+'\x08 \x7f' for char in '*FX3,3'])
			ser.write(s2b(s)+b'\x0b\r')

			attempts = attempts+1

		# See if we have any output from the beeb yet
		x = ser.read(1)
		if x:
			log(3, x)
			while ser.in_waiting:
				log(3, ser.in_waiting)
				x = ser.read(1)
				log(3, x, ser.in_waiting)

			# If we got the prompt, and nothing after it, 
			# then we should be OK to proceed
			if x == b'>':
				break

		if attempts % 2 == 0:
			# Maybe it's stuck in a high-speed mode, see if we can help it out
			baudrates = [9600, 19200, 78600, 38400, 4800, 2400, 1200, 600, 300, 150, 75]
			ser.baudrate = baudrates[(attempts // 2) % len(baudrates)]
			log(2, "    Trying to reset client from %d baud" % ser.baudrate)

			s = b''.join([
				b'         ',        # Flush out VDU23
				b'\x03\x15',         # Printer off, clear input
				b'OSCLI("FX7,7"):',  # Receive rate to 9600
				b'OSCLI("FX8,7"):',  # Transmit rate to 9600
				b'*FX156,2,252\r'    # Multiplier to x1
			])

			# Write characters slowly so that even at high baud
			# the beeb has time to process them
			for ch in s:
				time.sleep(0.01)
				ser.write(bytes([ch]))

			time.sleep(0.1)
			ser.baudrate = 9600

	# Assuming DSR is still active, we are connected and have
	# established reliable comms with the beeb
	if ser.dsr:
		log(0, "Link active")

		# Disable serial output now, and also disable VDU output
		# unless log level is high
		if loglevel >= 2:
			exec("*FX3,0")
		else:
			exec("*FX3,2")

		# Bootstrap the client
		send_init_program()

		log(0, "Ready")

		# In general operation, so long as the connection is
		# not dropped, respond to commands
		while ser.dsr:
			# Commands are four bytes long, so if we have all 
			# four then we can process it
			if ser.in_waiting >= 4:
				do_command()


	# If DSR goes high then we lost connection, so go back 
	# to the beginning
	log(0, "Connection lost")

