import fsc 
import osargs 
import osbgetbput 
import osfile 
import osfind 
import osgbpb 

from utils import log
from connection import ser

from send_code import *
from send_code_error import *


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
		fsbase+0x00: osfile.do_file,
		fsbase+0x03: osargs.do_args,
		fsbase+0x06: osbgetbput.do_bget,
		fsbase+0x09: osbgetbput.do_bput,
		fsbase+0x0c: osgbpb.do_gbpb,
		fsbase+0x0f: osfind.do_find,
		fsbase+0x12: fsc.do_fsc,

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



# Activation via *-command
def do_activate(a, x, y):
	log(1, "    *S (activate)")
	send_code_fromfile("data/activate.x")
	send_code_main(a, x, y)


# Client requested to be sent the main code
def do_main(a, x, y):
	log(1, "    M (main)")
	send_code_main(a, x, y)


