#!/usr/bin/env python3
"""
CloudWatch Group scanner
"""
import boto3
from datetime import datetime, timedelta
from pricing.price import get_log_group_storage_costs

SESSION = boto3.Session()
INSTANCE_PRICE_MAP = {}
START_TIME = datetime.now() - timedelta(days=30)
END_TIME = datetime.now()


def get_log_group_incoming_bytes(cloudwatch_client, log_group_name):
    """
    Get log group incoming bytes
    """
    response = cloudwatch_client.get_metric_statistics(
        Namespace="AWS/Logs",
        MetricName="IncomingBytes",
        Dimensions=[
            {"Name": "LogGroupName", "Value": log_group_name}
        ],
        StartTime=START_TIME,
        EndTime=END_TIME,
        Period=2592000,
        Statistics=["Sum"],
    )

    if response["Datapoints"]:
        return round(response["Datapoints"][0]["Sum"] / 1024 / 1024 / 1024, 2)

    return "N/A"


def query_cloudwatch_groups(region):
    """
    CloudWatch Group entrypoint
    """
    # pylint: disable=too-many-locals,too-many-branches
    cloudwatch_client = SESSION.client("cloudwatch", region_name=region)
    cloudwatch_logs_client = SESSION.client("logs", region_name=region)

    table_head = [
        "Group Name",
        "Retention",
        "Creation Time",
        "Stored GB",
        "Incoming GB",
        "Monthly Storage Cost *",
        "Log Group Class",
    ]
    table_data = []

    log_group_storage_costs = get_log_group_storage_costs(INSTANCE_PRICE_MAP, region)
    print(f"\n\n✨  Running in CloudWatch Group mode {region}")
    paginator = cloudwatch_logs_client.get_paginator("describe_log_groups")
    page_iterator = paginator.paginate()

    for page in page_iterator:
        for group in page["logGroups"]:
            group_name = group["logGroupName"]
            retention = group.get("retentionInDays", "N/A")
            creation_time = group.get("creationTime", "N/A")
            human_creation_time = datetime.fromtimestamp(creation_time / 1000).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            stored_bytes = group.get("storedBytes", "N/A")
            gigabytes = stored_bytes / 1024 / 1024 / 1024
            log_group_class = group.get("logGroupClass", "N/A")
            incoming_bytes = get_log_group_incoming_bytes(cloudwatch_client, group_name)

            table_data.append(
                [
                    group_name[:80],
                    retention,
                    human_creation_time,
                    round(gigabytes, 2),
                    incoming_bytes,
                    round(log_group_storage_costs * gigabytes, 2),
                    log_group_class,
                ]
            )

    return table_head, table_data
