
; Set cliv to point to new cli_handler address
cli_init
.(
	pha
	lda #<cli_handler : sta cliv
	lda #>cli_handler : sta cliv+1
	pla
	rts
.)

; CLI - if string starts with "S " consume it and activate
cli_handler
.(
	; Store command line pointer
	stx zp_cli_ptr
	sty zp_cli_ptr+1

	; Skip leading spaces and stars
	ldy #$ff
skipspacesstars
	iny
	lda (zp_cli_ptr),y
	cmp #32
	beq skipspacesstars
	cmp #'*'
	beq skipspacesstars

	; Check first letter is 'S'
	lda (zp_cli_ptr),y
	and #$df
	cmp #'S'
	bne chain

	; Check command ends here
	iny
	lda (zp_cli_ptr),y
	cmp #33
	bcs chain

	; Send activation command
	lda #'*'
	pha : pha
	ldy zp_cli_ptr+1
	jmp send_cmd

chain
	; Chain to next CLI handler
	ldy zp_cli_ptr+1
	jmp (oldcliv)
.)
