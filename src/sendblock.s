#include "gen/init.imp"

* = org
.(
	jmp start

	; Send a potentially large block of data

	; These values will get overwritten before execution
addr
	.word 0
len
	.word 0

start
	; Transfer address and length to zero page locations
	lda addr
	sta zp_block_ptr
	lda addr+1
	sta zp_block_ptr+1
	lda len
	sta zp_block_len
	lda len+1
	sta zp_block_len+1

	; Send the data
	jsr ser_send_block

	; Wait for continuation
	jmp ser_recv_code

#include "src/frag/ser_send_block.s"
.)

#print himem-*
