# Generate Makefile dependency data for assembly file includes

import re
import sys

includere = re.compile(r'^\W*#\W*include\W*"([^"]*)"\W*')
sourcere = re.compile(r'src/(.*).s')

deps = {}

def scan(filename):
	if filename not in deps:
		deps[filename] = set()

		try:
			fp = open(filename, "r")
		except FileNotFoundError:
			return deps[filename]

		try:
			for line in fp.readlines():
				m = includere.match(line)
				if m:
					childname = m.group(1)
					deps[filename].add(childname)
					deps[filename].update(scan(childname))
		finally:
			fp.close()

	return deps[filename]


for f in sys.argv[1:]:
	scan(f)
	
	m = sourcere.match(f)
	assert m
	basename = m.group(1)

	objname = 'data/%s.x' % basename
	labelsname = 'gen/%s.labels' % basename
	incname = 'gen/%s.inc' % basename

	print("%s: %s %s" % (objname, f, ' '.join(sorted(deps[f]))))

print("Deps: " + " ".join(deps.keys()))

