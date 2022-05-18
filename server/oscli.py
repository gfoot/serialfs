import re

import fs
from send_code_error import *
from send_code_main import *
from send_code_message import *

from utils import *


re_command = re.compile(r"[*]? *([a-zA-Z]+)(\.?)(.*)")

def handle(command, a, x, y):
	m = re_command.match(command)
	if not m:
		return False

	cmd, dot, rest = m.groups()
	cmd = cmd.upper()

	if dot:
		for commandname in commands:
			if commandname.startswith(cmd):
				cmd = commandname
				break

	if cmd not in commands:
		return False

	commands[cmd](cmd, rest, a, x, y)
	return True


def do_delete(cmd, rest, a, x, y):
	log(1, "    DELETE %s" % rest)
	
	filename = sanitize_filename(rest)

	f = fs.File(filename)

	if not f.exists:
		send_code_error_filenotfound()
		return

	try:
		f.delete()
	except:
		send_code_error_filelocked()
		return

	send_code_main(a, x, y)


def do_dir(cmd, rest, a, x, y):
	log(1, "    DIR %s" % rest)

	name = sanitize_filename(rest)

	if len(name) != 1 or name[0] not in fs.validchars:
		send_code_error(206, "Bad directory")
		return

	fs.setdir(name)

	send_code_main(a, x, y)


def do_info(cmd, rest, a, x, y):
	log(1, "    INFO %s" % rest)

	files = []
	for drive, path in fs.glob(rest):
		files.append(path)

	for filename in files:
		f = fs.File(filename)
		if not f.exists:
			send_code_error_filenotfound()
			return

		result = "%s %06X %06X %06X\r\n" % (
			(f.name+" "*18)[:18],
			f.addr_load & 0xffffff,
			f.addr_exec & 0xffffff,
			f.length & 0xffffff)

		send_code_message(result)

	send_code_main(a, x, y)


def do_rename(cmd, rest, a, x, y):
	log(1, "    RENAME %s" % rest)
	send_code_error(253, "Unsupported API")


commands = {
	"DELETE": do_delete,
	"DIR": do_dir,
	"INFO": do_info,
	"RENAME": do_rename,
}


