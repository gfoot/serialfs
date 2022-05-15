#include "gen/init.imp"

* = org
.(
	; Report an error

	jsr cli_init

	jmp error

#include "src/frag/clihandler.s"

error
	brk
	; server must append error number and message
.)

#print himem-*
