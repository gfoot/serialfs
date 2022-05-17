# Serial filing system server program
# 
# Listens for connections
# Sends initialization code
# Waits for commands
# Sends new code as required to execute commands
#
# Saved files are stored in the "storage" directory, along with
# 'inf' metadata files in what I believe is the standard format
# according to mdfs.net

import bootup
import session
import settings


settings.loglevel = 1
settings.allow_irq_during_recv = False


bootup.init()

while True:
	session.run()

