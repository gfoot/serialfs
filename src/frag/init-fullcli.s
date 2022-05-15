; This is a backup of an early version that sent any params
; of the "*S" command over the wire for host processing

* = $a00

org = *

cliv = $208

filev = $212
argsv = $214
bgetv = $216
bputv = $218
gbpbv = $21a
findv = $21c
fscv = $21e

oldcliv = *+$f0

zp_block_ptr = $80 ; => $c0?
zp_block_len = $82 ; => $c2?

zp_cli_ptr = $88 ; => $f8
zp_saved_a = $8a ; => $fa

acia_control = $fe08
acia_status = $fe08
acia_read = $fe09
acia_write = $fe09


entry
	jmp init

filevhandler ; $a05   $12 + string
	jsr fshandler
argsvhandler ; $a08   4zp
	jsr fshandler
bgetvhandler ; $a0b   0
	jsr fshandler
bputvhandler ; $a0e   0
	jsr fshandler
gbpbvhandler ; $a11   $d
	jsr fshandler
findvhandler ; $a14   filename, usually
	jsr fshandler
fscvhandler  ; $a17   params or string
	jsr fshandler

init
.(
	php
	sei

	ldy cliv : sty oldcliv
	ldy cliv+1 : sty oldcliv+1 
	ldy #<cli_handler : sty cliv
	ldy #>cli_handler : sty cliv+1

	plp
	rts
.)


activate
.(
	lda #6
	jsr callfscv

	ldx #fsvectorsend-fsvectors-1
loop
	lda fsvectors,x
	sta filev,x
	dex
	bpl loop

	; TODO: service call 15

	rts

callfscv
	jmp (fscv)

fsvectors
	.word filevhandler
	.word argsvhandler
	.word bgetvhandler
	.word bputvhandler
	.word gbpbvhandler
	.word findvhandler
	.word fscvhandler
fsvectorsend
.)


; Send multiple bytes
;
; Sends zp_block_len (16 bits) bytes
; from buffer pointed at by zp_block_ptr
;
; Clobbers A,X
ser_send
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


; Send one byte from A
; Clobbers nothing
ser_send_byte
.(
	pha

	; Wait for transmit data register empty
	lda #2
waitloop
	bit acia_status
	beq waitloop

	; Write the byte
	pla
	sta acia_write

	rts
.)


; CLI - if string starts with "S " consume it and send it
cli_handler
.(
	stx zp_cli_ptr
	sty zp_cli_ptr+1

	ldy #$ff
skipspacesstars
	iny
	lda (zp_cli_ptr),y
	cmp #32
	beq skipspacesstars
	cmp #'*'
	beq skipspacesstars

	lda (zp_cli_ptr),y
	and #$df
	cmp #'S'
	bne chain

	iny
	lda (zp_cli_ptr),y
	cmp #33
	bcs chain

;	php
;	sei

	sec
	tya
	adc zp_cli_ptr
	sta zp_block_ptr
	lda zp_cli_ptr+1
	adc #0
	sta zp_block_ptr+1
	
	ldx #$ff
findendloop
	inx
	cpx #$ff
	beq err
	iny
	lda (zp_cli_ptr),y
	cmp #13
	bne findendloop

	stx zp_block_len
	lda #0
	sta zp_block_len+1
	
	lda #'*'
	jsr ser_send_byte
	jsr ser_send

;	plp

done
	ldx zp_cli_ptr
	ldy zp_cli_ptr+1
	rts

err
	lda #'E'
	jsr $ffee

chain
	jsr done
	jmp (oldcliv)
.)

fshandler
	jsr ser_send_byte
	txa
	jsr ser_send_byte
	tya
	jsr ser_send_byte
	pla
	jsr ser_send_byte
	pla
	rts


ser_recv_code
.(
	lda #0
	sta 
.)


#print *-org
