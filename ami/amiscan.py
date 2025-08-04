#!/usr/bin/env python3
"""
AMI scanner
"""
from datetime import datetime, timedelta
import boto3

SESSION = boto3.Session()
END_TIME = datetime.now()
START_TIME = END_TIME - timedelta(days=30)


def query_ami(region):
    """
    AMI entrypoint
    """
    # pylint: disable=too-many-locals,too-many-branches
    print(f"\n\n✨  Running in AMI mode {region}")
    ec2_client = SESSION.client("ec2", region_name=region)
    paginator = ec2_client.get_paginator("describe_images")
    page_iterator = paginator.paginate(Owners=["self"])

    table_head = [
        "ImageId",
        "Name",
        "State",
        "Creation date",
        "Last launched",
        "Size in GB",
    ]
    table_data = []

    for page in page_iterator:
        for image in page["Images"]:
            size = 0
            image_id = image["ImageId"]
            image_name = image["Name"]
            image_state = image["State"]
            image_creation_date = image["CreationDate"]
            image_launch = image.get("LastLaunchedTime", "N/A")
            block_device_mapping = image.get("BlockDeviceMappings", [])
            for device in block_device_mapping:
                ebs = device.get("Ebs")
                if ebs:
                    volume_size = ebs.get("VolumeSize", "0")
                    if volume_size != "0":
                        size = int(size) + int(volume_size)

            table_data.append(
                [
                    image_id,
                    image_name,
                    image_state,
                    image_creation_date,
                    image_launch,
                    size,
                ]
            )

    return table_head, table_data
