# How the ROMless Serial Filing System works

## Initial connection

The \*FX2,1 call causes the BBC Micro to take input from the
serial system rather than from the keyboard.  At this stage the
regular VDU output is still active.

This causes the BBC Micro to take its CTS line low, and on the
PC end this is usually wired to DSR, so the PC becomes aware
that something is listening.  However the BBC is not sending
output to the serial port yet, so the first commands have to be
sent in the blind.  We also don't necessarily know what the port
settings need to be.

For stability's sake, the initial communication is done at 9600
baud, 8-N-1, which is the BBC's default.  The server sends a
\*FX3,1 command to direct output to the serial port instead of
the VDU system, and sees if it gets a '>' prompt in response.
If so, then great.  If not it tries again a few times.

If it's really not getting through, it starts experimenting with
sending commands using different port settings.  It does this
more carefully, one character at a time, and the command it
sends is one that should reset the BBC Micro to 9600 baud.  It's
still being sent in the blind, so after each change to the
settings it loops back and tries the \*FX3,1 command again to
see if things have improved.

## Uploading the initialisation code

Assuming it eventually gets through, the server knows that the
BBC is able to communicate and ready for BASIC commands.

The first thing we need to do is transfer some machine code that
will take over the communication on the BBC side, so we can
restore the regular input and output channels to the keyboard
and VDU system.

The code itself is going to go into page &0A, which is the
RS423's input buffer.  This is the only memory we'll use, so
it's fine to move PAGE down to &0E00 when this filing system is
active.  But we can't just start writing code there because
everything we send corrupts that bit of memory, so we need to
tee it up a bit.

We do that by initialising an empty BASIC string, and then
looping, reading characters from the serial port and storing
them in the string.  So these are the first BASIC commands we
send:

    >A$=""
    >FOR I%=0 TO 253:A$=A$+GET$:N.

After sending these commands, the server sends the 254 bytes of
initialisation code.  With that sent, it can then send a
compound command which does several things:

* \*FX3,0 - Switch output back to the VDU

* \*FX2,2 - Switch input back to the keyboard, but leave the
serial input subsystem active enough that we can still use it
ourselves

* \*FX204,1 - Disable the RS423 input buffer - this prevents
the OS from reading the serial port itself, so we can do it 
when we want to instead; and it also ensures no more characters
get written to the RS423 input buffer in page &0A, so our code
will be safe

* $&A00=A$ - write the string containing the initialisation code
into page &0A.  It's convenient that BASIC can do this all in
one go.

* CALL &A00 - execute the code

These five things are all bundled together in a single-line
command, using colons as usual.

## Initialisation code

The initialisation code [src/init.s](src/init.s) now runs.  It is split into two parts.
The low half of the page contains some one-off initialisation
code, while the upper half of the page contains permanent code
that will remain resident from now on.

The pernanent code especially includes some shared routines that
are used later on by all sorts of other code, such as
subroutines to send and receive bytes, and especially a
subroutine to download new code blocks.

The first thing the initialisation code does is inform the server that it is 
running, by sending an 'I' byte.  Then it changes the serial settings to 
76800 baud, and the server does the same.  This speed seems very reliable so 
long as the client is actively waiting when data comes from the server.

After that the initialisation code performs some more initial setup,
installing a CLI handler (for star commands, so that it
can respond to \*S), and ends by executing the ser\_recv\_code
subroutine, which waits for the server to send some new code to
run.  Most code that gets uploaded ends by calling this function
again to allow the server to direct what happens next.

In this case though, the code that gets loaded ([src/message.s](src/message.s))
just prints a message and then returns control to the caller on
the BBC end, which is the BASIC prompt.

## The CLI handler

The CLI handler routine is a bit odd.  It kind of needs to be
present all the time, but there isn't space for it in the shared
area - so it lives in the low half of the page, and gets swapped
in and out.  Any time we return control to the system, we must
make sure the CLI handler is loaded.  This is usually done by
loading [src/main.s](src/main.s), which includes a copy of the CLI handler
and a few ways to return control to the system.

## Filing system APIs

When the CLI handler detects the \*S command, it sends a command
with code '\*' to the server, and the server sends the code for
[src/activate.s](src/activate.s).  This is a fairly standard filing system
activation routine, which performs some notifications and
overwrites the filing vectors with its own ones.

The actual routines that handle the filing API calls are not,
however, loaded.  Instead there are stubs which just notify the
server which API was executed, and - similar to the handling for
\*S - the server sends specific code to execute depending upon
which API was called and what the register values were.

The filing system APIs vary quite a bit regarding what data
needs to be sent.  OSFILE always requires an 18-byte parameter
block and a filename to be sent, so that's packaged up in
[src/osfile.s](src/osfile.s).  FSC is not so simple though - the action to
take varies a lot depending on context, so the server makes more
decisions based on the value in the A register, and asks the
client to send specific memory blocks such as filenames using
generic code rather than sending specific FSC-handling code to
the client.

## Messages and errors

If the server needs the client to display a message, or emit an
error, it loads [src/message.s](src/message.s) or [src/error.s](src/error.s).  The latter in
particular is a bit special because it doesn't get a chance to
load [src/main.s](src/main.s) as usual after it runs - it's going to trigger
a BRK, and the language is going to pick that up straight away.
So [src/error.s](src/error.s) needs to also contain core functionality like
the CLI handler.

