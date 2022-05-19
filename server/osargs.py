from send_code_main import *
from send_code_recv import *
from send_code_send import *
from send_code_error import *

import fs


# Pointer to last command line tail
tail_ptr = 0

def set_tail_ptr(ptr):
	global tail_ptr
	tail_ptr = ptr


# OSARGS
def do_args(a, x, y):
	log(1, "    OSARGS &%02x &%02x %d" % (a, x, y))

	if y == 0:
		if a == 0:
			return do_args_get_fs_id(a, x, y)
		if a == 1:
			return do_args_get_cmd_tail_ptr(a, x, y)
		if a == 0xff:
			return do_args_flush_open_files(a, x, y)

	else:
		if a == 0:
			return do_args_get_file_ptr(a, x, y)
		if a == 1:
			return do_args_set_file_ptr(a, x, y)
		if a == 2:
			return do_args_get_file_len(a, x, y)
		if a == 0xff:
			return do_args_flush_file(a, x, y)

	log(2, "        unsupported")
	send_code_main(a, x, y)


# OSARGS with no handle
def do_args_nh(a, x, y):
	if a == 0:
		return do_args_get_fs_id(a, x, y)
	if a == 1:
		return do_args_get_cmd_tail_ptr(a, x, y)
	if a == 0xff:
		send_code_main(a, x, y) # flush open files - no-op

	log(2, "        unsupported")
	send_code_main(a, x, y)


def do_args_get_fs_id(a, x, y):
	log(2, "        get filing system ID")
	send_code_main(15, x, y)

def do_args_get_cmd_tail_ptr(a, x, y):
	log(2, "        get command line tail ptr")
	block = [tail_ptr & 0xff, tail_ptr >> 8, 0, 0]
	send_code_recv(x, 4, block)
	send_code_main(a, x, y)

def do_args_flush_open_files(a, x, y):
	log(2, "        flush open files")
	fs.flushall()
	send_code_main(a, x, y) # no-op


def do_args_get_file_ptr(a, x, y):
	log(2, "        get file #%d ptr" % y)

	f = fs.checkhandle(y)
	if not f:
		send_code_error_channel()
		return

	pos = [0,0,0,0]
	write32(pos, 0, f.pos)

	send_code_recv(x, 4, pos)

	send_code_main(a, x, y) # todo


def do_args_set_file_ptr(a, x, y):
	log(2, "        set file #%d ptr" % y)

	f = fs.checkhandle(y)
	if not f:
		send_code_error_channel()
		return

	pos = send_code_send(x, 4)

	f.seek(read32(pos, 0))

	send_code_main(a, x, y) # todo


def do_args_get_file_len(a, x, y):
	log(2, "        get file #%d length" % y)

	f = fs.checkhandle(y)
	if not f:
		send_code_error_channel()
		return

	pos = [0,0,0,0]
	write32(pos, 0, f.length)

	send_code_recv(x, 4, pos)

	send_code_main(a, x, y) # todo


def do_args_flush_file(a, x, y):
	log(2, "        flush file #%d" % y)

	f = fs.checkhandle(y)
	if not f:
		send_code_error_channel()
		return

	f.flush()

	send_code_main(a, x, y) # no-op

