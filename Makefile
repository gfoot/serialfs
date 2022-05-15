SRCS=$(wildcard src/*.s)
OBJS=$(patsubst src/%.s, data/%.x, $(SRCS))

all: $(OBJS)

data/%.x gen/%.labels: src/%.s
	xa $< -o data/$*.x -l gen/$*.labels

gen/%.imp: gen/%.labels
	python genimports.py $< $@

Deps: Makefile
	python gendeps.py $(SRCS) > $@

include Deps

clean:
	-rm gen/* data/* Deps
