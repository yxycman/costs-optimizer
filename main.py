#!/usr/bin/env python3

import click
from ec2.ec2scan import query_ec2
from ebs.ebsscan import query_ebs
from rds.rdsscan import query_rds


@click.command(context_settings={"show_default": True})
@click.help_option("-h", "--help")
@click.option(
    "-m",
    "--modes",
    required=True,
)
@click.option(
    "-r",
    "--regions",
    required=True,
)
@click.option("-v", "--verbose", is_flag=True)
def main(**options):
    """
    Main entrypoint
    """

    modes = options["modes"]
    regions = options["regions"]
    verbose = options["verbose"]

    for region in regions.split(","):
        for mode in modes.split(","):
            match mode:
                case "ebs":
                    query_ebs(region)
                case "ec2":
                    query_ec2(verbose, region)
                case "rds":
                    query_rds(verbose, region)


if __name__ == "__main__":
    main()
