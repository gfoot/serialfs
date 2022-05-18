from send_code import *
from utils import *


# Send the "main" code, which restores the system to the
# default state ready for more CLI and filing system commands.
# This isn't quite the same state as after initialization but
# is close enough.
def send_code_main(a, x, y, sec=False):
	send_code_fromfile("data/main.x", 
		(3, a), (4, x), (5, y),
		(6, 0x40 if sec else 0))

# Send the "main" code but instead of returning to the caller,
# jump to some other address (e.g. for *RUN)
def send_code_mainexec(a, x, y, addr):
	send_code_fromfile("data/main.x", 
		(3, a), (4, x), (5, y),
		(6, 0xff),
		(7, addr & 0xff), (8, (addr>>8) & 0xff))

