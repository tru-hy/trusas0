#!/bin/bash
R=..

if [ $# -lt 2 ]
then
	echo "usage: $0 <bluetooth address> <output file>" >&2
	exit 1
fi

BT_ADDR=$1
OUTFILE=$2

if [ -e $OUTFILE ]
then
	echo "Output file exists! Won't overwrite!" >&2
	exit 1
fi

touch $OUTFILE
$R/nexus/physiology.py $BT_ADDR > $OUTFILE &
tail -f $OUTFILE |$R/plot/signal_plotter.py -s E

