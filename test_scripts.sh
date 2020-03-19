#!/bin/sh

set -eu

TMPDIR="tests/tmpdir"
FTDATA="foretold_data.json"
CSSEDIR="data/CSSE-COVID-19/csse_covid_19_data/csse_covid_19_time_series/"

mkdir -p "$TMPDIR"

echo
echo "*** testing ./estimate.py ***"
echo

if [ -f "$FTDATA" ] && [ -d "$CSSEDIR" ] ; then
    ./estimate.py data/definition-example.xml -o "$TMPDIR/est.xml" -O "$TMPDIR/est.csv" -f "$FTDATA" -C "$CSSEDIR"
else
    echo "!!! Skipping estimate.py. Get $FTDATA and $CSSEDIR"
fi

echo
echo "*** testing ./parameterize.py ***"
echo

./parameterize.py data/definition-example.xml "$TMPDIR/params" -P 0.1,0.2,0 -P [1,0.1],-0.2,[0.5]

