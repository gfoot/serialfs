
; Send multiple bytes
;
; Sends zp_block_len (16 bits) bytes
; from buffer pointed at by zp_block_ptr
;
; Clobbers A,X
ser_send_block
.(
	; If low byte is not zero, increment the high byte,
	; due to the way the dec carry works
	lda zp_block_len
	beq noincrement
	inc zp_block_len+1
noincrement

	; Is len actually zero?
	ora zp_block_len+1
	beq done

loop
	; Prepare the next byte
	ldx #0
	lda (zp_block_ptr,x)
	tax

	; Wait for transmit data register empty
	lda #2
waitloop
	bit acia_status
	beq waitloop

	; Write the byte
	stx acia_write

	; Check if there's more to send
	dec zp_block_len
	bne nocarry
	dec zp_block_len+1
	beq done
nocarry

	; Advance to next byte
	inc zp_block_ptr
	bne loop
	inc zp_block_ptr+1
	jmp loop
	
done
	rts
.)


