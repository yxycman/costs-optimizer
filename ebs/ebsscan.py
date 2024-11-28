#!/usr/bin/env python3

import boto3
from pricing.price import get_ebs_price
from tabulate import tabulate

SESSION = boto3.Session()
EBS_PRICE_MAP = {}


def query_ebs(region):
    """
    EBS entry point
    """
    print(f"\nRunning in EBS mode {region}")

    client = SESSION.client("ec2", region_name=region)
    paginator = client.get_paginator("describe_volumes")
    page_iterator = paginator.paginate()

    table_head = [
        "id",
        "created",
        "status",
        "attachment",
        "size",
        "type",
        "cost",
        "future cost",
        "saving",
    ]
    table_data = []

    for page in page_iterator:
        for volume in page["Volumes"]:
            volume_id = volume["VolumeId"]
            volume_size = volume["Size"]
            volume_state = volume["State"]
            volume_date = volume["CreateTime"].strftime("%Y-%m-%d")
            volume_type = volume["VolumeType"]
            volume_attachment = volume.get("Attachments")
            ec2_attachment = None
            if volume_attachment:
                ec2_attachment = volume_attachment[0].get("InstanceId")

            volume_data = [
                volume_id,
                volume_date,
                volume_state,
                ec2_attachment,
                volume_size,
                volume_type,
            ]

            current_cost = round(
                get_ebs_price(EBS_PRICE_MAP, volume_type, region) * volume_size, 3
            )
            if ec2_attachment:
                if volume_type == "gp2":
                    future_cost = round(
                        get_ebs_price(EBS_PRICE_MAP, "gp3", region) * volume_size, 3
                    )
                    if isinstance(current_cost, str) and isinstance(future_cost, str):
                        saving = "N/A"
                    else:
                        saving = round((current_cost - future_cost), 2)
                    volume_data.append(f"{current_cost}$")
                    volume_data.append(f"{future_cost}$")
                    volume_data.append(f"{saving}$")
                else:
                    volume_data.append(f"{current_cost}$")
            else:
                volume_data.append(f"{current_cost}$")
                volume_data.append(None)
                volume_data.append(f"{current_cost}$")

            table_data.append(volume_data)

    if table_data:
        print(tabulate(table_data, headers=table_head, tablefmt="github"))
