# Epidemic Forecasting library and tools

Libraries and utilities for data handling, estimation and modelling of epidemics. Part of https://github.com/epidemics/ project.

* Needs Python 3.7+, git, poetry.
* Install requirements with `poetry install`.

## Pipeline overview

(Uppercase filenames are just placeholders, others are changeable defaults.)

### Fetch and create data

* Foretold predictions fetched into `foretold_data.json` with `fetch_foretold.py`.
* CSSE github data fetched&updated into `data/CSSE-COVID-19/` with `fetch_csse.sh`.
* Create/update GleamViz `DEF.xml` by hand or in the GUI.

### Estimate and parameterize

* Estimate the infected populations from the above using `estimate.py`, creating `DEF.est.xml`.
* Create multiple versions `PREFIX_XXX.xml` of a simulation def using `parameterize.py`. The project currently uses `-P [1.0,0.85,0.7],[0.2,0.7],[0.0,0.3,0.4,0.5]`.
  * This also autonames the simulations with params, but the parameters are not read from the name.

### Run Gleam

The simulations imported into GleamViz reside in `GLEAMDIR/data/sims`, one dir each.

* Open GleamViz. Remove any simulations. (Warning - this also removes the on-disk dirs!)
* Import all definitions (one by one).
* Run all the simulations (normal users are allowed 2 at a time).
* For each finished sim, click "Retrieve simulation".
  * Do **not** "export" them, this is slow and unnecessary.

### Create data for the web

* Optionally update the `data/country_selection.tsv` file with country/area/city selection.
  * Needs the Gleam IDs and types (kinds), found in `md_cities.csv`, `md_countries.csv` etc. (Will likely be automated?)
* Run `./process_h5s.py ALL_GVH5_DIRS ...` to create `line-data.csv`.
  * Currently needs exactly the right 24 simulation dirs with parameters above in `P`.
  * Parameters are inferred from `EVERY_GVH5_DIR/definition.xml`.
* Publish `line-data.csv` to the web where-ever [lines.js](https://github.com/epidemics/covid/blob/master/src/server/static/js/lines.js#L75) expects it.
  * Beware of caching in GCS buckets! See https://github.com/epidemics/covid/issues/116

## Used data sources and notes

### Foretold COVID estimates

https://github.com/epidemics/covid

### COVID

https://github.com/CSSEGISandData/COVID-19/

### Geography

https://openflights.org/data.html - airport coordinates
https://simplemaps.com/data/world-cities - populations
https://simplemaps.com/data/us-cities - us cities, counties and states

(list incomplete)