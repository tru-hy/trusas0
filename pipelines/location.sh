#!/bin/bash
R=..

if [ $# -lt 1 ]
then
	echo "Need an output file!" >&2
	exit 1
fi

OUTFILE=$1

if [ -e $OUTFILE ]
then
	echo "Output file exists! Won't overwrite!" >&2
	exit 1
fi

touch $OUTFILE

$R/android/location.py > $OUTFILE &
tail -f $OUTFILE |$R/plot/location_plotter.py

