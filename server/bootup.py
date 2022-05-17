import os
import subprocess
import re
import settings
import sys


# Parse xa's "labels" file syntax
re_labels = re.compile(r"^([^,]*), *0x([0-9a-f]*), *([0-9]*),.*")


# Load global symbols from xa's "labels" file
def loadsyms(filename):
	with open(filename) as f:
		syms = {}
		for line in f.readlines():
			m = re_labels.match(line)
			assert m
			sym,value,ns = m.groups()
			if ns == "0":
				if sym not in syms:
					syms[sym] = value
				else:
					syms[sym] = None
		f.close()
	remove = set()
	for sym,value in syms.items():
		if value is None:
			remove.add(sym)
	for sym in remove:
		del syms[sym]
	return syms


# Convert xa's "labels" file into actual labels that can be 
# included in other assemblies
#
# This only exports globals, to avoid name conflicts
def write_imp(syms, outfile):
	lines = ["%s = $%s\n" % (sym,syms[sym]) for sym in sorted(syms.keys())]

	with open(outfile, "w") as of:
		of.writelines(lines)
		of.close()


# Assemble a file of 6502 code
def assemble(inputfilename, outputfilename, labelfilename=None):
	print("Assembling %s" % outputfilename)

	cmd = ["xa", inputfilename, "-o", outputfilename, "-M"]
	if labelfilename:
		cmd.extend(["-l", labelfilename])

	try:
		result = subprocess.run(cmd, check=True)
	except subprocess.CalledProcessError:
		print("\nAssembly of %s failed" % inputfilename)
		sys.exit(1)


# Assemble all the code
def init():

	# Assemble "init" first
	assemble("src/init.s", "data/init.x", "gen/init.labels")

	# Parse the labels from "init"
	syms = loadsyms("gen/init.labels")
	
	# Write out init.imp for including in other files
	write_imp(syms, "gen/init.imp")

	# Check the maximum allowable code size
	var_himem = int(syms["himem"], 16)
	var_org = int(syms["org"], 16)
	settings.max_code_size = var_himem - var_org

	print(settings.max_code_size)
	assert settings.max_code_size == 0x9c

	# Assemble the rest of the files
	for f in os.listdir("src"):
		if f.endswith(".s") and f != "init.s":
			basename = f[:-2]
			assemble("src/"+f, "data/"+basename+".x")
 

