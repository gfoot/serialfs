#include "gen/init.imp"

* = org
.(
	jmp start

	; Receive a large block of data (multiple pages)
	;
	; addr is the address of the start of the block
	; length is the 16-bit length of the block
addr
	.word 0
length
	.word 0

start
	; Transfer address to zero page
	lda addr
	sta zp_block_ptr
	lda addr+1
	sta zp_block_ptr+1

	; Transfer length too, and adjust it so that we can easily
	; perform a 16-bit decrement and test for zero later on
	lda length+1
	sta zp_block_len+1
	lda length
	beq noincrement
	inc zp_block_len+1
noincrement
	sta zp_block_len

	; Is there actually no data to transfer?
	ora zp_block_len+1
	beq done

	php
	sei

	; OK, we're ready
	jsr ser_send_byte

loop
	; Read a byte
	jsr ser_recv_byte

	; Store the byte
	ldx #0
	sta (zp_block_ptr,x)

	; Check if there's more to read
	dec zp_block_len
	bne nocarry
	dec zp_block_len+1
	beq done
nocarry

	; Advance to the next byte
	inc zp_block_ptr
	bne loop
	inc zp_block_ptr+1
	jmp loop

done
	plp
	jmp ser_recv_code
.)

#print himem-*
