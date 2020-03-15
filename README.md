# Foretold + CSSE -> Gleamviz

## Install

Needs Python 3.6+, `git` and `curl`.

Install the python dependencies using e.g.:

```sh
python -m pip install pandas numpy dateutil unidecode requests
```

## Fetch data

Run `./fetch_csse.sh` to get/update the CSSE published confirmed cases into `data/CSSE-COVID-19`.

Run `./fetch_foretold.sh CHANNEL_ID` to fetch Foretold estimates into `foretold_data.json`. (`CHANNEL_ID` is non-public.)

## Running

Then run `python convert.py` in the git direcotry (to find libs and data). This can produce:

* `INPUT.updated.xml` (with `INPUT.xml`, the GleamViz simulation definition XML), the updated file for GleamViz.
* `estimated_active.csv` (with `-O ...`), the city estimates exported as CSV.

Minimal arguments are just `python convert.py INPUT.xml`.

```text
usage: convert.py [-h] [-o OUTPUT_XML] [--output_xml_limit OUTPUT_XML_LIMIT]
                  [-O OUTPUT_EST] [-r REGIONS] [-f FORETOLD] [-C CSSE_DIR]
                  [-D BY_DATE] [-T] [-d]
                  [INPUT_XML]

positional arguments:
  INPUT_XML             GleamViz template to use (optional). (default: None)

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_XML, --output_xml OUTPUT_XML
                        Override output XML path (default is
                        'INPUT.updated.xml'). (default: None)
  --output_xml_limit OUTPUT_XML_LIMIT
                        Only output top # of most-infected cities in the XML.
                        (default: None)
  -O OUTPUT_EST, --output_est OUTPUT_EST
                        Also write the city estimates as a csv file. (default:
                        None)
  -r REGIONS, --regions REGIONS
                        Regions csv file to use. (default: data/regions.csv)
  -f FORETOLD, --foretold FORETOLD
                        Foretold JSON to use. (default: foretold_data.json)
  -C CSSE_DIR, --csse_dir CSSE_DIR
                        Directory with CSSE 'time_series_19-covid-*.csv'
                        files. (default: data/CSSE-COVID-19/csse_covid_19_data
                        /csse_covid_19_time_series/)
  -D BY_DATE, --by_date BY_DATE
                        Use latest Foretold and CSSE data before this
                        date&time (no interpolation is done). (default: now)
  -T, --show_tree       Debug: display final region tree with various values.
                        (default: False)
  -d, --debug           Display debugging mesages. (default: False)
```

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


### Recheck countries in structure (name duplicates)

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
