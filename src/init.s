org = $a00
himem = $a9c

cliv = $208

filev = $212
argsv = $214
bgetv = $216
bputv = $218
gbpbv = $21a
findv = $21c
fscv = $21e

zp_block_ptr = $c0 ; => $b0?
zp_block_len = $c2 ; => $b2?

zp_cli_ptr = $f8 ; => $a8?

acia_control = $fe08
acia_status = $fe08
acia_read = $fe09
acia_write = $fe09


* = org

.(

init
.(
	; Send a byte so the server knows we're running
	lda #'I'
	jsr ser_send_byte

	; Wait a little before upgrading the speed
	ldx #0
	ldy #$80
delay
	inx
	bne delay
	iny
	bne delay

	; Upgrade connection speed
	lda #7 : ldx #8 : jsr $fff4               ; 19200 baud
	lda #8 : ldx #8 : jsr $fff4               ; 19200 baud
	lda #156 : ldx #1 : ldy #252 : jsr $fff4  ; x4 speed

	; Turn off fake ACIA interrupts
	lda #232 : ldx #0 : ldy #0 : jsr $fff4

	; Register CLI handler
	php
	sei
	
	ldy cliv : sty oldcliv
	ldy cliv+1 : sty oldcliv+1 

	jsr cli_init

	plp

	jmp ser_recv_code
.)


#include "src/frag/clihandler.s"


#print himem-*
	.dsb himem-*, $00

; Send the registers and command ID, then wait for code 
; from the remote host to determine what to do next.
; 
; The command ID is on the stack, along with a dummy byte.
; This means that code can 'jsr' to here, and the low byte 
; of the jsr return address becomes the command code, with
; the high byte ignored.  The idea is that the code after
; the 'jsr' doesn't actually get returned to, it's just a
; compact way for the filing system API handlers to pass in
; distinct command codes.  But it's up to the host what 
; code runs, and it could send back code that does indeed
; indirectly 'return' from the jsr.
&send_cmd
.(
	jsr ser_send_byte
	txa
	jsr ser_send_byte
	tya
	jsr ser_send_byte
	pla
	jsr ser_send_byte
	pla
.)


; Receive new code
&ser_recv_code
.(
	;lda #'W'
	;jsr $ffee

	; Disable interrupts so that we don't miss any bytes
	php
	sei

	; Tell server we're ready to receive
	jsr ser_send_byte

	; Read number of bytes to receive
	jsr ser_recv_byte

	; Index into code block, decrements towards zero
	tax

loop
	; Read byte
	jsr ser_recv_byte
	; Store in code block
	sta org-1,x

	; Advance
	dex
	; More to receive?
	bne loop

	plp

	jmp org
.)


; Send one byte from A
;
; Clobbers nothing
&ser_send_byte
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


; Receive one byte, into A
;
; Clobbers nothing
&ser_recv_byte
.(
	; Wait for data
	lda #$75
waitloop
	bit acia_status
	beq waitloop

	lda acia_status
	and #$74
	bne error

	; Read a byte
	lda acia_read
	rts

error
	lda #'E'
	jsr $ffee
lp
	jmp lp
.)


top
	.dsb org+$e9-*, $00
#print *-top

&filevhandler ; cmd=$eb   $12 + string
	jsr send_cmd
&argsvhandler ; cmd=$ee   4zp
	jsr send_cmd
&bgetvhandler ; cmd=$f1   0
	jsr send_cmd
&bputvhandler ; cmd=$f4   0
	jsr send_cmd
&gbpbvhandler ; cmd=$f7   $d
	jsr send_cmd
&findvhandler ; cmd=$fa   filename, usually
	jsr send_cmd
&fscvhandler  ; cmd=$fd   params or string
	jsr send_cmd

&oldcliv
	.word org

#print *-org-256

.)

