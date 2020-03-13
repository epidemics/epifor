#!/bin/sh
set -eu
D=CSSE-COVID-19

cd data
if [ -e "$D" ]; then
    echo "Updating CSSE github"
    cd "$D"
    git pull
    cd ..
else
    echo "Cloning CSSE github"
    git clone https://github.com/CSSEGISandData/COVID-19 "$D"
fi