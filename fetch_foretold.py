#!/usr/bin/env python3

import click

from epifor.data.fetch_foretold import fetch_foretold


@click.command()
@click.option("-c", "--channel_id", envvar="FORECASTIO_CHANNEL", help="UUID of the channel.")
@click.option("-o", "--output_path", type=click.Path(), default="foretold_data.json", help="Path to write to.")
def run_fetch(channel_id, output_path):
    """Fetch the data from foretold.io."""
    if not channel_id:
        click.echo("Please, set channel_id, either using -c parameter, or in the FORECASTIO_CHANNEL environment variable.")
        exit(-1)
    data = fetch_foretold(channel_id)
    with open(output_path, "wb") as outfile:
        outfile.write(data)


if __name__ == "__main__":
    run_fetch()
