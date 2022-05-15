# Convert xa's "labels" file into actual labels that can be 
# included in other assemblies
#
# This only exports globals, to avoid name conflicts


import re
import sys

exp = re.compile(r"^([^,]*), *0x([0-9a-f]*), *([0-9]*),.*")

def loadsyms(filename):
	with open(filename) as f:
		syms = {}
		for line in f.readlines():
			m = exp.match(line)
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


if __name__ == "__main__":
	infile = sys.argv[1]
	outfile = sys.argv[2]

	syms = loadsyms(infile)

	lines = ["%s = $%s\n" % (sym,syms[sym]) for sym in sorted(syms.keys())]

	with open(outfile, "w") as of:
		of.writelines(lines)
		of.close()

