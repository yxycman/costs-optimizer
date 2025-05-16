#!/usr/bin/env python3

from datetime import datetime
import boto3
from pricing.price import get_ebs_price, get_snapshot_price

SESSION = boto3.Session()
EBS_PRICE_MAP = {}
SNAPSHOT_PRICE_MAP = {}


def query_ebs(region):
    """
    EBS entry point
    """
    print(f"\n\nRunning in EBS volume mode {region}")

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

    return table_head, table_data


def query_ebs_snapshots(region):
    """
    EBS snapshot entrypoint
    """
    print(f"\n\nRunning in EBS snapshot mode {region}")

    ec2_client = SESSION.client("ec2", region_name=region)
    account_id = SESSION.client("sts").get_caller_identity().get("Account")
    paginator = ec2_client.get_paginator("describe_snapshots")
    page_iterator = paginator.paginate(OwnerIds=[account_id])

    table_head = [
        "id",
        "description (crop 100)",
        "volume size",
        "snapshot size (Feb 2025+)",
        "state",
        "start time",
        "tier",
        "cost/GB",
        "cost/Month",
    ]
    table_data = []

    for page in page_iterator:
        for snapshot in page["Snapshots"]:
            snapshot_id = snapshot["SnapshotId"]
            snapshot_description = snapshot.get("Description", "N/A")
            volume_size = snapshot.get("VolumeSize", "N/A")
            snapshot_size = round(snapshot.get("FullSnapshotSizeInBytes", "N/A"))
            snapshot_state = snapshot["State"]
            snapshot_start_time = datetime.strftime(snapshot["StartTime"], "%Y-%m-%d")
            snapshot_tier = snapshot.get("StorageTier", "N/A")
            snapshot_size_gb = (
                snapshot_size / 1073741824 if snapshot_size != "N/A" else "N/A"
            )

            snapshot_cost, snapshot_price = get_snapshot_price(
                SNAPSHOT_PRICE_MAP, snapshot_tier, snapshot_size_gb, region
            )

            snapshot_data = [
                snapshot_id,
                snapshot_description[:100],
                volume_size,
                snapshot_size_gb,
                snapshot_state,
                snapshot_start_time,
                snapshot_tier,
                f"{snapshot_cost}$",
                f"{round(snapshot_price, 2)}$",
            ]
            table_data.append(snapshot_data)

    return table_head, table_data
