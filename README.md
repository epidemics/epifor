# Epidemic Forecasting library and tools

**Note: Track issues for this repo in https://github.com/epidemics/covid/issues**

Libraries and utilities for data handling, estimation and modelling of epidemics. Part of https://github.com/epidemics/ project.

* Needs Python 3.7+, git, poetry.
* Install requirements with `poetry install`.

## Quickstart

### Install / preparation

* First, [install Poetry](https://python-poetry.org/docs/#installation)
* Then, install the lib and its dependencies (e.g. in virtualenv)
  
```sh
git clone https://github.com/epidemics/epifor
cd epifor

poetry install
```

* If you want to upload to the GCS bucket storege for the web, [get gsutil](https://cloud.google.com/storage/docs/gsutil_install) and configure it with your goole account.

```sh
gsutil config
```

* Create copies of the config files (any names will do). Do not modify the original config.yaml or definition-example.xml

```sh
cp config.yaml config-local.yaml
cp data/definition-example.xml definition-local.xml
```

* Edit `config-local.yaml`: set "gleamviz_dir" and "foretold_channel" (this is non-public, sorry)
* Make sure that directory `YOUR_GLEAM_DIR/data/sims/` exists or create it

### Running a batch of simulations

**NOTE:** Do not run any of the pipeline commands while GleamViz is running.

* Once a day (and before first run) update the data files.

```sh
./gleambatch.py update
```

* Your `definition-local.xml` can be updated via GleamViz import+export or just a text editor.
* Update the settings (countries, parameters, ...) in `config-local.yaml`.

```sh
./gleambatch.py generate config-local.yaml definition-local.xml
```

* Copy-paste the path of the created batch-file (or the suggested command).
* Run GleamViz, all the created simulations should be there.
* Run all simulations (there is a limit on how many at once you can run, perhaps also some daily limit?)
* Retrieve all simulations via the blue buttons (Can be done in parallel. You do not need to export them!)

```sh
./gleambatch.py process out/batch-XXXXX/batch.yaml
```

* This creates files in directory `out/batch-XXXXX/`

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
