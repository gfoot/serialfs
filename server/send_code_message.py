from send_code import *
from utils import *


# Send code to cause the client to print a message which is 
# embedded in the code
def send_code_message(message):
	with open("data/message.x", "rb") as fp:
		code = list(fp.read())
		fp.close()

	codelen = len(code)
	capacity = settings.max_code_size - len(code)
	for pos in range(0, len(message), capacity):
		submessage = message[pos:pos+capacity]
		code[1] = len(submessage)
		code[codelen:] = s2b(submessage[::-1])

		send_code(bytes(code), "message")

