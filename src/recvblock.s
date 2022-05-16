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

	; Set ~RTS on, to prepare for turning it off again as a
	; signal to the server
	ldx #$55 : jsr setaciacontrol

	; XOFF
	lda #21 : jsr ser_send_byte

	; Wait a bit so the server can see that ~RTS is on
.(
	ldx #0
delay
	iny
	bne delay
	inx
	bne delay
.)

	; Start with this negative
	dey
	sty blocksizerem

	; Disable interrupts
	php : sei

	; Set ~RTS off, to signal the server to send a data block
	ldx #$15 : jsr setaciacontrol

loop
	; Start of new block if blocksizerem is negative
	ldy blocksizerem
	bpl receive

	; Read up to 'blocksize' more bytes before the next break.
	; 'blocksizerem' counts from blocksize-1 to -1.
	ldy blocksize
	dey
	sty blocksizerem

receive
	; Read a byte
	jsr ser_recv_byte

	; Store the byte
	ldx #0
	sta (zp_block_ptr,x)

	; Was that the second-last byte of the block?
	dec blocksizerem
	bmi nextbyte         ; last byte
	bne notendofblock    ; neither

	; If it was the second-last byte of the block...
	
	; Re-enable interrupts briefly - this is ok because there's
	; only one more byte to read, so we don't need to read it 
	; urgently, as it won't get overwritten if we don't
	plp
	php : sei

	; Set ~RTS off, to signal the server to send the next block
	;
	; We do this significantly in advance because it actually
	; takes quite a while for the remote side to respond.  So
	; long as we still get to the ser_recv_byte above before
	; the data arrives, all is good.
	ldx #$15 : jsr setaciacontrol

	bne nextbyte   ; always taken

notendofblock
	; Set ~RTS on, to tell the server we're reading the block
	ldx #$55 : jsr setaciacontrol

nextbyte
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
