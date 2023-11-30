import serial
import settings

# Default serial settings on the beeb seem to be 9600 8-N-1
#
# Experiments show this can easily be increased to 76800, with 
# 8-N-2 maybe being more reliable at that speed.  Receiving at
# higher speeds doesn't work because of the way the ACIA is 
# wired in the Beeb, but transmitting at higher speeds might 
# also be possible.  Not sure if Python Serial supports 
# asymmetric settings.
ser = serial.Serial(settings.device, 9600, 8, "N", 1, timeout=1)

