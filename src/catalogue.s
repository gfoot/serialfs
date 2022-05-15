#include "gen/init.imp"

* = org
.(
	jmp start

	; These values will get overwritten before execution
count
	.byte 0

start

	; Are there any entries to show at all?
	lda count
	beq done

	; Loop over the entries
loop

	; Y is an index within the filename
	ldy #0

	php
	sei

	; Ready for next filename
	jsr ser_send_byte

filenameloop
	jsr ser_recv_byte
	sta filename,y
	beq filenameloopend
	iny
	jmp filenameloop
filenameloopend

	plp

	; Even entries on the left, odd entries on the right
	bit oddeven
	bmi odd

	; Even entry
.(
	; Newline and a few spaces
	jsr $ffe7
	lda #' '
	jsr $ffee
	jsr $ffee

	; Count field with for 18 to align odd column later on
	ldx #18

	; Make flag negative so next entry will be odd
	dec oddeven
	jmp printloop
.)

	; Odd entry
odd
.(
	; Print enough spaces to align the column based on X value
	lda #' '
	jsr $ffee
	dex
	bne odd

	; Make flag positive so next entry will be even
	inc oddeven
.)

	; Print the file name
printloop
	lda filename-1,y
	jsr $ffee
	dex ; count remaining field width
	dey
	bne printloop

	; Loop if there are more filenames to display
	dec count
	bne loop

done
	; Newline
	jsr $ffe7

	; Ready for new code
	jsr ser_send_byte

	jmp ser_recv_code

oddeven
	.byte 0

filename
	.word 0,0,0,0,0,0,0,0
.)

#print himem-*
