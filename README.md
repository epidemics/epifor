# Epidemic Forecasting library and tools

**Note: Track issues for this repo in https://github.com/epidemics/covid/issues**

Libraries and utilities for data handling, estimation and modelling of epidemics. Part of https://github.com/epidemics/ project.

* Needs Python 3.7+, git, poetry.
* Install requirements with `poetry install`.

## Short guide (with new pipeline runner)

(Uppercase filenames are just placeholders, others are changeable defaults.)

### Install / preparation

* First, [install Poetry](https://python-poetry.org/docs/#installation)

```sh
git clone https://github.com/epidemics/epifor
cd epifor

poetry install

# Do not modify the original config.yaml or definition-example.xml
cp config.yaml config-local.yaml
cp data/definition-example.xml definition-local.xml
```

* If you want to upload to the GCS bucket storege for the web, [get gsutil](https://cloud.google.com/storage/docs/gsutil_install) and configure it with your goole account.

```sh
gsutil config
```

* Edit `config-local.yaml`: set "gleamviz_dir" and "foretold_channel" (this is non-public, sorry)
* (optional) Run GleamViz and import and edit the xml definition, then export it.
* Make sure that directory `YOUR_GLEAM_DIR/data/sims/` exists or create it

### Running a batch of simulations

* Update your `definition-local.xml` (text editor or GleamViz import+export)
* **NOTE:** Do not run any scripts while GleamViz is running.
* **NOTE:** Before creating a new batch, run GleamViz and remove all simulations. (Clearing `/GLEAM_DIR/data/sims` by hand is not enough.)

```sh
./run_pipeline.py config-local.yaml -P definition-local.xml
```

* Run GleamViz, all the created simulations should be there.
* Run all simulations (there is a limit on how many at once you can run, also some daily limit?)
* Retrieve all simulations (can be done in parallel). (You do not need to export them!)

```sh
./run_pipeline.py config-local.yaml -S
```
* This creates the file `out/DATE-TIME-gleam.json`
* Push it to `data-CHANNEL-gleam.json`, where channel is `staging` (testing), `main` or anything else (will beavailable at URL )

```sh
./push_to_bucket.sh out/DATE-TIME-gleam.json data-staging-gleam.json
```

## Installing and running GLEAMViz in Linux

When you install GleamVIz in Linux, it adds `LD_LIBRARY_PATH="GLEAMviz/libs/"` to your configuration in `.bashrc`.
I would suggest you remove it as gleam comes with its own copies of some low-level libraries.
(It caused some issues on my system due to libc conflicts.)

If you do the above, run GleamViz with `LD_LIBRARY_PATH="GLEAMviz/libs/" GLEAMviz/gleamviz`.

Some people installing GleamViz on Linux have the issue that GLEAMViz crashes on start (sometimes complaining about some Qt dependency, I do not remember the exact error message).
The root cause I found was that GleamViz ships with a part of libc, namely its own `libm.so.6` from libc 2.29 (mine is 2.30). Renaming it helped resolve it for me and Daniel.

## Pipeline overview (mostly outdated by the above)

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
