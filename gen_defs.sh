#!/bin/bash

REQS=""
for MITIG in 0.0 0.3 0.4 0.5; do
    for SEASON in 0.1 0.7 0.85; do
        for AIRTRAF in 0.2 0.7; do
            REQS="$REQS -P $SEASON,$AIRTRAF,$MITIG"
        done
    done
done

python convert.py "$@" $REQS


