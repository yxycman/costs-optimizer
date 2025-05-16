#!/usr/bin/env python3

import click
from tabulate import tabulate
from gpt.ask import query_gpt
from ec2.ec2scan import query_ec2
from ebs.ebsscan import query_ebs, query_ebs_snapshots
from rds.rdsscan import query_rds


def tabulate_data(ai, mode, table_head, table_data):
    """
    Tabulate data
    """

    tabulated_data = tabulate(
        table_data, headers=table_head, tablefmt="github", floatfmt=".2f"
    )
    print(tabulated_data)
    if ai:
        query_gpt(mode, table_head, tabulated_data)


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

    mode_functions = {
        "ebs": [query_ebs, query_ebs_snapshots],
        "ec2": [query_ec2],
        "rds": [query_rds],
    }

    for region in regions.split(","):
        for mode in modes.split(","):
            if mode in mode_functions:
                for func in mode_functions[mode]:
                    table_head, table_data = func(region)
                    if table_head and table_data:
                        tabulate_data(ai, mode, table_head, table_data)


if __name__ == "__main__":
    main()
