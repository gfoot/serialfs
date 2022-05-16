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
blocksizerem
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

	; Set ~RTS on to prevent data flow
	ldx #$55 : jsr setaciacontrol

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

	sty blocksizerem

	; Disable interrupts
	php : sei

	; Set ~RTS off, to allow data flow
	ldx #$15 : jsr setaciacontrol

loop
	; Start of new block?
	ldy blocksizerem
	bne receive

	; Read up to 'blocksize' more bytes before the next break
	ldy blocksize
	sty blocksizerem

receive
	; Read a byte
	jsr ser_recv_byte

	; Store the byte
	ldx #0
	sta (zp_block_ptr,x)

	; Set ~RTS on to prevent data flow
	ldx #$55 : jsr setaciacontrol

	; Check if there's more to read
	dec zp_block_len
	bne nocarry
	dec zp_block_len+1
	beq done
nocarry

	; Is it time for a little break?
	dec blocksizerem
	bne nextbyte
	
	; Re-enable interrupts briefly
	plp
	php : sei

	; Set ~RTS off, to allow data flow
	;
	; We do this significantly in advance because it actually
	; takes quite a while for the remote side to respond.  So
	; long as we still get to the ser_recv_byte above before
	; the data arrives, all is good.
	ldx #$15 : jsr setaciacontrol

nextbyte
	; Advance to the next byte
	inc zp_block_ptr
	bne loop
	inc zp_block_ptr+1
	jmp loop

done
	; Set ~RTS off so that the server doesn't hang up
	ldx #$15 : jsr setaciacontrol
	plp
	jmp ser_recv_code


setaciacontrol
	lda #156
	ldy #0
	jmp $fff4
.)

#print himem-*
