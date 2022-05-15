#include "gen/init.imp"

* = org
.(

	; Activate the filing system
	jsr activate

	jmp ser_recv_code

activate
.(
	; Don't do it if we're already active
	lda fscv
	cmp #<fscvhandler
	bne notme
	lda fscv+1
	cmp #>fscvhandler
	bne notme
	rts

notme
	; We are not already active, notify current filing 
	; system of impending change
	lda #6
	jsr callfscv

	; Write new filing system vectors
	ldx #fsvectorsend-fsvectors-1
loop
	lda fsvectors,x
	sta filev,x
	dex
	bpl loop

	; Issue ROM service call 15 and return
	lda #$8f : ldx #15 : ldy #0
	jmp $fff4

	; Call through the FSC vector
callfscv
	jmp (fscv)

	; My filing system vector values
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

.)

#print himem-*
