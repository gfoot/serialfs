.(
org = $1100
* = org

; Print the value of the accumulator in hex as two digits
;
; Clobbers A
&printhex
.(
	pha
	lsr : lsr : lsr : lsr
	jsr printhexdigit
	pla
	and #15
printhexdigit
	cmp #10
	bcc notletter
	adc #6
notletter
	adc #48
	jmp $ffee
.)

	.word org
.)


