from send_code_error import *
from send_code_main import *
from utils import *

import fs

# BGET
def do_bget(a, x, y):
	log(1, "    OSBGET")

	f = fs.getfile(y)
	if not f:
		send_code_error_channel()
		return

	if not f.allow_read:
		send_code_error(212, "Write only")
		return

	a = fs.bget(y)

	if a is None:
		send_code_main(0, x, y, sec=True)
	else:
		send_code_main(a, x, y)

# BPUT
def do_bput(a, x, y):
	log(1, "    OSBPUT")

	f = fs.getfile(y)
	if not f:
		send_code_error_channel()
		return

	if not f.allow_write:
		send_code_error(193, "Read only")
		return

	fs.bput(y, a)

	send_code_main(a, x, y)

