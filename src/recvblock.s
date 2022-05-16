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
blocksize
	.byte 0

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

	; Initialise Y to trigger the start of a new block
	ldy #0

	php
	sei

	; Set ~RTS on to prevent data flow
	;lda #156 : ldx #$55 : ldy #0 : jsr $fff4
	lda #$55 : sta acia_control

	; XOFF
	lda #21 : jsr ser_send_byte

	; Wait a bit
.(
	ldx #0
delay
	iny
	bne delay
	inx
	bne delay
.)

loop
	; Start of new block?
	cpy #0
	bne receive

	; Wait a bit
.(
	ldx #$f0
delay
	iny
	bne delay
	inx
	bne delay
.)

	; Read up to 'blocksize' more bytes before the next break
	ldy blocksize

	; Disable interrupts
	php : sei

	; XON
	lda #23 : jsr ser_send_byte
	
	; Set ~RTS off, to allow data flow
	;lda #156 : ldx #$15 : ldy #0 : jsr $fff4
	lda #$15 : sta acia_control

receive
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

	; Is it time for a little break?
	dey
	bne nextbyte
	
	; XOFF
	lda #21 : jsr ser_send_byte
	
	; Set ~RTS on to prevent data flow
	;lda #156 : ldx #$55 : ldy #0 : jsr $fff4
	lda #$55 : sta acia_control

	; Re-enable interrupts briefly
	plp

nextbyte
	; Advance to the next byte
	inc zp_block_ptr
	bne loop
	inc zp_block_ptr+1
	jmp loop

done
	plp
	plp
	jmp ser_recv_code
.)

#print himem-*
