#!/usr/bin/env python3

import click
from tabulate import tabulate
from gpt.ask import query_gpt
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
@click.option(
    "-a",
    "--ai-suggestions",
    is_flag=True,
    default=False,
)
def main(**options):
    """
    Main entrypoint
    """

    modes = options["modes"]
    regions = options["regions"]
    ai = options["ai_suggestions"]

    for region in regions.split(","):
        for mode in modes.split(","):
            match mode:
                case "ebs":
                    table_head, table_data = query_ebs(ai, region)
                case "ec2":
                    table_head, table_data = query_ec2(ai, region)
                case "rds":
                    table_head, table_data = query_rds(ai, region)

            if table_head and table_data:
                tabulated_data = tabulate(
                    table_data, headers=table_head, tablefmt="github"
                )
                print(tabulated_data)
                if ai:
                    query_gpt(mode, table_head, tabulated_data)


if __name__ == "__main__":
    main()
