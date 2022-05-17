import settings

from connection import ser
from utils import log

from send_code import *
from send_code_message import *
from send_code_main import *



# Helper for sending simple commands for the client to execute
# during early initialization, when it's just normal serial
# text comms
def exec(s):
	log(3, " exec: %s" % s)
	ser.write(s2b(s+'\r'))


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

	# Disable serial output now, and also disable VDU output
	# unless log level is high
	if settings.loglevel >= 2:
		exec("*FX3,0")
	else:
		exec("*FX3,2")

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


