#include "gen/init.imp"

* = org
.(
	; Receive a small block of data (up to 256 bytes)

	; These values will get overwritten before execution
	lda #0   ; address low
	ldx #0   ; address high
	ldy #0   ; length

.(
	sta zp_block_ptr
	stx zp_block_ptr+1

	;lda #'R'
	;jsr $ffee

	php
	sei

	; Signal that we're ready to receive
	jsr ser_send_byte

	; Receive all the bytes, backwards
loop
	dey
	cpy #$ff
	beq done
	jsr ser_recv_byte
	sta (zp_block_ptr),y
	jmp loop

done
	plp

	; Wait for continuation
	jmp ser_recv_code
.)

#include "src/frag/ser_send_block.s"
.)

#print himem-*
