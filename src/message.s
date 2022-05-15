#include "gen/init.imp"

* = org
.(
	; Print a message

	ldx #0   ; length

loop
	lda message-1,x
	jsr $ffee
	dex
	bne loop

	jmp ser_recv_code

message
.)

#print himem-*
