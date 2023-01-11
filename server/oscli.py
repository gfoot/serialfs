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

	log(1, "    %s %s" % (cmd, rest))
	commands[cmd](cmd, rest, a, x, y)
	return True


# Split 'command' on spaces, up to a maximum number of 
# arguments - then the last one gets the rest
#
# Arguments are stripped and double-quotes removed if present.
# Double-quotes can be used to quote spaces and generally 
# follow BBC BASIC's rules.
def split_string(command, maxargs=255):
	# Split on quotes first
	# "test" => "", "test", ""
	# one "two" three => "one ", "two", " three"
	# "test ""embedded"" quotes" => "", "test ", "", "embedded", "", " quotes", ""
	spl1 = command.strip().split('"')

	# Replace spaces in unquoted (even) segments with nuls
	for i in range(0, len(spl1), 2):
		spl1[i] = spl1[i].replace(' ', '\0')

	# Empty unquoted segments other than first and last should
	# be single double-quote characters
	for i in range(2, len(spl1)-2, 2):
		if not spl1[i]:
			spl[i] = '"'

	# Join it together again, then split on nuls
	spl2 = ''.join(spl1).split('\0', maxargs-1)

	# Convert any nuls in the last argument back to spaces
	if spl2:
		spl2[-1] = spl2[-1].replace('\0', ' ')

	return spl2


def parse_drive(s):
	try:
		return int(s)
	except:
		return -1


def do_delete(cmd, rest, a, x, y):
	filename = sanitize_filename(rest)

	f = fs.file(filename)

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
	name = sanitize_filename(rest)

	if len(name) != 1 or name[0] not in fs.validchars:
		send_code_error(206, "Bad directory")
		return

	fs.setdir(name)

	send_code_main(a, x, y)


def do_info(cmd, rest, a, x, y):
	files = []
	for drive, path in fs.glob(rest):
		files.append(path)

	for filename in files:
		f = fs.file(filename)
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
	send_code_error(253, "Unsupported API")


def do_drive(cmd, rest, a, x, y):
	drive = parse_drive(sanitize_filename(rest))

	if drive < 0:
		send_code_error(205, "Bad drive")
		return

	if fs.drive(drive):
		send_code_main(a, x, y)
		return

	send_code_error(205, "Drive not ready")


def do_din(cmd, rest, a, x, y):
	args = split_string(rest)
	if len(args) == 1:
		drive = fs.current_drive
	else:
		drive = parse_drive(args[0])

	if drive < 0:
		send_code_error(205, "Bad drive")
		return

	if fs.mount(drive, args[-1]):
		send_code_main(a, x, y)
		return

	send_code_error(214, "Disc image not found")

def do_dcat(cmd, rest, a, x, y):
	mounts = sorted(fs.listmounts())
	if not mounts:
		send_code_message("No disc images found\r\n")
		send_code_main(a, x, y)
		return

	send_code_message("Available disc images to mount:\r\n")
	for f in mounts:
		send_code_message("    "+f+"\r\n")
	send_code_main(a, x, y)


commands = {
	"DELETE": do_delete,
	"DIR": do_dir,
	"DRIVE": do_drive,
	"INFO": do_info,
	"RENAME": do_rename,
	"DCAT": do_dcat,
	"DIN": do_din,
}


