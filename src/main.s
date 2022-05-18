#include "gen/init.imp"

* = org

.(
	jmp start

vara
	.byte 0
varx
	.byte 0
vary
	.byte 0
exec
	.byte 0
execaddr
	.word 0

start
	;lda #'M'
	;jsr $ffee

	jsr cli_init

	lda vara
	ldx varx
	ldy vary

	bit exec

	clc
	bvc nosetcarry
	sec
nosetcarry

	bmi do_exec
	rts

do_exec
	jmp (execaddr)

#include "src/frag/clihandler.s"

.)

#print himem-*
