from send_code import *
from utils import *

# Send code to cause a BRK error on the client
def send_code_error(errno, message):
	with open("data/error.x", "rb") as fp:
		code = list(fp.read())
		fp.close()

	code.append(errno)
	code.extend(s2b(message))
	code.append(0)

	send_code(bytes(code), "error")


def send_code_error_filenotfound():
	send_code_error(214, "File not found")

def send_code_error_filelocked():
	send_code_error(195, "File locked")

