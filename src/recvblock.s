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
aciacontrolbyte
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

	; ~RTS starts off
	ldx #$15 : jsr setaciacontrol

	; XOFF
	lda #21 : jsr ser_send_byte

	; Wait a bit so the server can see the current ~RTS state
.(
	ldx #0
delay
	iny
	bne delay
	inx
	bne delay
.)

	; Start with this negative to signal end of block
	dey
	sty blocksizerem

	; Disable interrupts
	php : sei

	; Signal the server to send a data block
	jsr togglerts

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
	bne notendofblock

	; If it was the second-last byte of the block...
	
	; Re-enable interrupts briefly - this is ok because there's
	; only one more byte to read, so we don't need to read it 
	; urgently, as it won't get overwritten if we don't
	plp
	php : sei

	; Toggle ~RTS to signal the server to send the next block
	;
	; We do this significantly in advance because it actually
	; takes quite a while for the remote side to respond.  So
	; long as we still get to the ser_recv_byte above before
	; the data arrives, all is good.
	;
	; So after this happens, we go around and read the final 
	; byte of the previous block, process it, and then loop
	; again to start the next block, and it takes even more 
	; than this amount of time for the server to actually 
	; send that first byte
	;
	; This limits the throughput to about 3.5K per second 
	; with interrupts enabled and 32-byte block :(
	; 
	; Larger block sizes don't give enough interrupt 
	; responsiveness.
	jsr togglerts

notendofblock
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


togglerts
	lda aciacontrolbyte
	eor #$40
	tax
setaciacontrol
	stx aciacontrolbyte
	lda #156
	ldy #0
	jmp $fff4
.)

#print himem-*
