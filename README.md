# ROMless Serial Filing System for the BBC Micro

This is a remote filing system server for the BBC Micro that
doesn't require any ROMs or other additions to the BBC Micro
itself.

The BBC is connected to a Linux PC running the server software,
using a serial cable from the RS423 port to a USB serial port on
the PC.  When serial input is enabled on the BBC using \*FX2,1
the server automatically sends initialisation sequences,
including filing system driver code, so there's no need for a
filing system ROM.

After that type \*S on the BBC Micro to select the serial filing
system, just as you would use \*DISC for example, and core
filing system functions will now operate on files stored in a
directory on the server.

## Step by step

With the server running, on the BBC type \*FX2,1

    BBC Comupter
    
    Turbo MMC
    
    BASIC
    
    >*FX2,1
    
    Initialising SerialFS...
    
    Use *S to select SerialFS
    >_

Select SerialFS and try a \*.

    >*S
    >*.
    
      BABY              LOADER
      O.1               O.2
      O.3               O.4
      REPTON1           RUNTEST
      TEST              TESTPRG
    >_

This directory has a custom copy of Repton 3, and some test
programs.  Let's run a BASIC test program that reads the
attributes of another file, and run a machine code test program
as well:

    >CH."TESTPRG"
      32400001
    TEST 4000 1 12 77
    >*/RUNTEST
    Hello world
    >_

My server also has a custom copy of Repton 3, modified to load
at E00 and avoid page A, and this runs well too.

## Supported APIs

Aside from the "\*S" command to select the filing system, the
following APIs are currently supported:

* OSFILE &FF (load)
* OSFILE &00 (save)
* OSFILE &05 (read attrs)
* FSCV 2,3,4 (variants of \*RUN)
* FSCV 5 (\*CAT)

This is enough to cover most simple usage.  The next tranche
that are probably worth implementing are probably DELETE, INFO,
and maybe DIR, and sequential file access (BGET, BPUT).  It's a
deep rabbit hole though.

## How it works

See [How It Works](howitworks.md).


