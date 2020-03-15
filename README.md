# Foretold + CSSE -> Gleamviz

## Install

Needs Python 3.6+, `git` and `curl`.

Install the python dependencies using e.g.:

```sh
python -m pip install pandas numpy dateutil unidecode requests
```

## Fetch data

Run `./fetch_csse.sh` to get/update the CSSE published confirmed cases into `data/CSSE-COVID-19`.

Run `./fetch_foretold.sh CHANNEL_ID` to fetch Foretold estimates into `data/foretold_data.json`. (`CHANNEL_ID` is non-public.)

## Running

You will need a GleamViz simulation definition XML with a single simulation.

Then run `python convert.py YOUR_SIM.xml` in the git direcotry. This will produce:

* `YOUR_SIM.updated.xml` with all the pops estimated to be non-zero.
* `estimated_active.csv` with the estimates exported as CSV.

## Used data sources and notes

### COVID

https://github.com/CSSEGISandData/COVID-19/

### Geography

https://openflights.org/data.html - airport coordinates
https://simplemaps.com/data/world-cities - populations
https://simplemaps.com/data/us-cities - us cities, counties and states


### Unused

https://github.com/datasets/population-city
https://www.kaggle.com/max-mind/world-cities-database/data
https://github.com/datasets/population-city


### Recheck countries in structure

Duplicate in MD gibraltar
Duplicate in MD djibouti
Duplicate in MD christmas island
Duplicate in MD malta
Duplicate in MD niue
Duplicate in MD dominica
Duplicate in MD montserrat
Duplicate in MD guam
Duplicate in MD liberia
Duplicate in MD bermuda
Duplicate in MD norfolk island
Duplicate in MD st barthelemy
Duplicate in MD grenada
Duplicate in MD mauritius
Duplicate in MD luxembourg
Duplicate in MD guernsey
Duplicate in MD curacao
Duplicate in MD jersey
Duplicate in MD isle of man
Duplicate in MD barbados
Duplicate in MD lebanon
Duplicate in MD anguilla
Duplicate in MD singapore
Duplicate in MD kuwait
Duplicate in MD aruba
Duplicate in MD monaco
Duplicate in MD bahrain
