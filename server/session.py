import serial
import time

import commands
import init

from utils import *
from connection import ser


attempts = 0

def attempt_connection():
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

	global attempts
	attempts = attempts+1


def check_for_prompt():
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
			return True
	return False


def try_reset_client_settings():
	baudrates = [9600, 19200, 78600, 38400, 4800, 2400, 1200, 600, 300, 150, 75]
	ser.baudrate = baudrates[(attempts // 2) % len(baudrates)]
	log(2, "    Trying to reset client from %d baud" % ser.baudrate)

	s = b''.join([
		b'         ',        # Flush out VDU23
		b'\x03\x15',         # Printer off, clear input
		b'OSCLI("FX7,7"):',  # Receive rate to 9600
		b'OSCLI("FX8,7"):',  # Transmit rate to 9600
		b'*FX156,150,0\r'    # Default settings
	])

	# Write characters slowly so that even at high baud
	# the beeb has time to process them
	for ch in s:
		time.sleep(0.01)
		ser.write(bytes([ch]))

	time.sleep(0.1)
	ser.baudrate = 9600


# Default serial settings on the beeb seem to be 9600 8-N-1
#
# Experiments show this can easily be increased to 76800, with 
# 8-N-2 maybe being more reliable at that speed.  Receiving at
# higher speeds doesn't work because of the way the ACIA is 
# wired in the Beeb, but transmitting at higher speeds might 
# also be possible.  Not sure if Python Serial supports 
# asymmetric settings.
#ser = serial.Serial(settings.device, 9600, 8, "N", 1, timeout=1)

STATE_RESET = 0
STATE_LISTEN = 1
STATE_CONNECT = 2
STATE_INIT = 3
STATE_CONNECTED = 4
STATE_DISCONNECTED = 5

state = STATE_RESET


def run():
	global attempts
	global state

	if state == STATE_RESET:
		# Reset to slow speed for initial connection
		ser.baudrate = 9600

		# Wait for a connection
		log(0, "")
		log(0, "Listening")

		state = STATE_LISTEN
		return

	if state == STATE_LISTEN:
		if not ser.dsr:
			time.sleep(0.1)
			return

		# The beeb is open for input now, but not output yet.
		# Wait until we see a prompt characte (">"), and 
		# occasionally send a command to enable serial output
		# until it appears.
		log(0, "Line open")
		attempts = 0
		state = STATE_CONNECT
		return
		
	if state == STATE_CONNECT:
		if not ser.dsr:
			state = STATE_DISCONNECTED
			return

		if not ser.in_waiting:
			attempt_connection()

		# See if we have any output from the beeb yet
		if check_for_prompt():
			state = STATE_INIT
			return

		# Maybe it's stuck in a high-speed mode,
		# see if we can help it out
		if attempts % 2 == 0:
			try_reset_client_settings()

		return

	if state == STATE_INIT:
		if not ser.dsr:
			state = STATE_DISCONNECTED
			return

		# Assuming DSR is still active, we are connected and have
		# established reliable comms with the beeb
		log(0, "Link active")

		# Bootstrap the client
		init.send_init_program()

		log(0, "Ready")
		state = STATE_CONNECTED
		return

	if state == STATE_CONNECTED:
		if not ser.dsr:
			state = STATE_DISCONNECTED
			return

		# In general operation, so long as the connection is
		# not dropped, respond to commands

		# Commands are four bytes long, so if we have all 
		# four then we can process it
		if ser.in_waiting >= 4:
			commands.do_command()

		return

	if state == STATE_DISCONNECTED:
		# If DSR goes high then we lost connection, so go back 
		# to the beginning
		log(0, "Connection lost")
		state = STATE_RESET
		return

