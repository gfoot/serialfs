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

## Server Installation

The instructions assume a Debian-like operating system but they should be similar for other Linux based OSs.

Change to your home directory:  
`cd ~/`
 
Install the dependencies:  
`sudo apt-get install git python3  python3-pip python3-venv xa65`

Add your user to the dialout group so you can access the serial device:  
`sudo usermod -a -G dialout $USER`

Clone the serialfs repository and change directory into it:  
`git clone https://github.com/gfoot/serialfs.git && cd serialfs`
 
Setup a Python virtual environment to keep dependencies contained from the OS:  
`python3 -m venv .venv`

Install the Python dependencies:  
`.venv/bin/python3 -m pip install -r requirements.txt`

Check the settings match your environment by opening the settings file in a text editor:  
`vim server/settings.py`  

N.B: "handshake" can be one of "cts" or "dsr", depending on how your serial device is wired. If in doubt, try both.

Create the storage directory:  
`mkdir -p storage/DEFAULT`

## Running SerialFS

### On the Server

Change into the serialfs directory:  
`cd ~/serialfs`

Start SerialFS:  
`.venv/bin/python3 server/serialfs-server.py`

Stopping SerialFS:  
`Ctrl` + `c`

### On the BBC
With the server running, on the BBC type \*FX2,1

    BBC Computer
    
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

