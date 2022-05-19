from utils import *
from send_code_main import *
from send_code_error import *
from send_code_send import *

import fs


# OSFIND
def do_find(a, x, y):
	log(1, "    OSFIND &%02x" % a)

	if a == 0:
		do_find_close(a, x, y)
	else:
		do_find_open(a, x, y)


def do_find_close(a, x, y):
	if y == 0:
		fs.closeall()
	else:
		if not fs.closefile(y):
			send_code_error_channel()
			return

	send_code_main(a, x, y)


def do_find_open(a, x, y):
	filename = send_code_sendstring(x+y*256, 255)

	handle = fs.openfile(filename, (a&0x40) != 0, (a&0x80) != 0)

	send_code_main(handle, x, y)

