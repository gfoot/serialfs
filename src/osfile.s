#include "gen/init.imp"

* = org
.(
	jmp start

	; These values will get overwritten before execution
operation
	.byte 0
blockaddr
	.word 0

start
	; Send the OSFILE block
	lda blockaddr
	sta zp_block_ptr
	lda blockaddr+1
	sta zp_block_ptr+1
	lda #$12
	sta zp_block_len
	lda #0
	sta zp_block_len+1
	jsr ser_send_block

	; Look up the filename pointer
	lda blockaddr
	sta zp_block_ptr
	lda blockaddr+1
	sta zp_block_ptr+1
	ldy #0
	lda (zp_block_ptr),y
	tax
	iny
	lda (zp_block_ptr),y
	stx zp_block_ptr
	sta zp_block_ptr+1
	
	; Send the filename
.(
	ldy #0
loop
	lda (zp_block_ptr),y
	jsr ser_send_byte
	cmp #33
	bcc done
	iny
	bne loop

	; Filename too long - terminate it anyway
	lda #13
	jsr ser_send_byte

done
.)

	; Wait for new code
	jmp ser_recv_code

#include "src/frag/ser_send_block.s"
.)

#print himem-*
