#!/usr/bin/env python3

import re
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from pricing.price import get_ec2_price

SESSION = boto3.Session()
AVAILABLE_INSTANCE_TYPES = set()
INSTANCE_PRICE_MAP = {}
END_TIME = datetime.now()
START_TIME = END_TIME - timedelta(days=30)


def check_instance_name(instance):
    """
    EC2 name
    """
    instance_name = "N/A"
    instance_tags = instance.get("Tags")
    if instance_tags:
        for tag in instance_tags:
            if tag["Key"] == "Name":
                instance_name = tag.get("Value")

    return instance_name


def check_instance_type(client, recommended_instance):
    """
    EC2 type existence
    """
    result = False

    if recommended_instance not in AVAILABLE_INSTANCE_TYPES:
        try:
            result = client.describe_instance_types(
                InstanceTypes=[recommended_instance]
            )
        except ClientError as exception:
            if exception.response["Error"]["Code"] == "InvalidInstanceType":
                pass
            else:
                raise
    else:
        result = True

    return result


def check_recommendation(client, instance_kind, mode):
    """
    EC2 recommendation check
    """
    instance_class = instance_kind.split(".")[0]
    instance_size = instance_kind.split(".")[1]
    instance_type = instance_class[0]
    instance_generation = instance_class[1]
    instance_recommendation = False

    if re.match("^t", instance_type):
        if instance_generation in ["2", "3"]:
            recommended_instance = instance_type
            if mode == "arm":
                recommended_instance += f"4g.{instance_size}"
            else:
                recommended_instance += f"3a.{instance_size}"
            if check_instance_type(client, recommended_instance):
                AVAILABLE_INSTANCE_TYPES.add(recommended_instance)
                instance_recommendation = recommended_instance

    elif re.match("^c|^m|^r", instance_type):
        if re.match("2|3|4|5|6|7", instance_generation):
            recommended_instance = instance_type
            if mode == "arm":
                recommended_instance += f"6g.{instance_size}"
            else:
                recommended_instance += f"6a.{instance_size}"
            if (
                check_instance_type(client, recommended_instance)
                and recommended_instance != instance_kind
            ):
                AVAILABLE_INSTANCE_TYPES.add(recommended_instance)
                instance_recommendation = recommended_instance

    if instance_recommendation == instance_kind:
        return "N/A"

    return instance_recommendation


def check_ec2_utilization(cloudwatch_client, instance_id):
    """
    EC2 utilization check
    """
    response = cloudwatch_client.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[
            {"Name": "InstanceId", "Value": instance_id},
        ],
        StartTime=START_TIME,
        EndTime=END_TIME,
        Period=3600,
        Statistics=["Average"],
    )

    data_points = response["Datapoints"]
    total_usage = sum(data_point["Average"] for data_point in data_points)
    if len(data_points):
        average_usage = total_usage / len(data_points)
        max_usage = max(data_point["Average"] for data_point in data_points)
        min_usage = min(data_point["Average"] for data_point in data_points)
    else:
        average_usage = 0
        max_usage = 0
        min_usage = 0

    return f"AVG: {round(average_usage, 2)}, MAX: {round(max_usage, 2)}, MIN: {round(min_usage, 2)}"


def check_replacement(ec2_client, instance_data, instance_config_map, instance_arch):
    """
    EC2 replacement check
    """
    instance_kind = instance_config_map["instance_kind"]
    instance_os = instance_config_map["instance_os"]
    region = instance_config_map["instance_region"]
    current_node_price = instance_config_map["instance_price"]

    instance_replacement = check_recommendation(
        ec2_client, instance_kind, instance_arch
    )
    if instance_replacement:
        if instance_os == "Windows" and instance_arch == "arm":
            instance_data.append("no Graviton for Windows")
        else:
            future_node_price = get_ec2_price(
                INSTANCE_PRICE_MAP, instance_replacement, instance_os, region
            )
            if isinstance(current_node_price, str) or isinstance(
                future_node_price, str
            ):
                instance_data.append("N/A")
            else:
                saving = round((current_node_price - future_node_price), 2)
                instance_data.append(
                    f"{instance_replacement} {future_node_price}$ (save:{saving}$)"
                )
    else:
        instance_data.append("N/A")


def query_ec2(ai, region):
    """
    EC2 entrypoint
    """
    print(f"\nRunning in EC2 mode {region}")

    ec2_client = SESSION.client("ec2", region_name=region)
    paginator = ec2_client.get_paginator("describe_instances")
    page_iterator = paginator.paginate()

    table_head = [
        "id",
        "name (crop 20)",
        "os",
        "started",
        "monitoring",
        "current",
        "future x86",
        "future arm",
        "30 days load",
    ]
    table_data = []

    for page in page_iterator:
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                instance_name = check_instance_name(instance)
                print(f"Checking {instance_id}")

                instance_state = instance["State"]["Name"]
                instance_kind = instance["InstanceType"]
                instance_os = instance["PlatformDetails"]
                instance_date = datetime.strftime(instance["LaunchTime"], "%Y-%m-%d")
                if instance_os == "Linux/UNIX":
                    instance_os = "Linux"
                instance_monitoring = instance["Monitoring"]["State"]

                current_node_price = get_ec2_price(
                    INSTANCE_PRICE_MAP, instance_kind, instance_os, region
                )
                instance_data = [
                    instance_id,
                    instance_name[:20],
                    instance_os[:10],  # here could be some exotic OS'
                    instance_date,
                    instance_monitoring,
                    f"{instance_kind} {current_node_price}$",
                ]

                instance_config_map = {
                    "instance_kind": instance_kind,
                    "instance_data": instance_data,
                    "instance_os": instance_os,
                    "instance_region": region,
                    "instance_price": current_node_price,
                }

                check_replacement(ec2_client, instance_data, instance_config_map, "x86")
                check_replacement(ec2_client, instance_data, instance_config_map, "arm")

                cloudwatch_client = SESSION.client("cloudwatch", region_name=region)
                if instance_state == "running":
                    instance_data.append(
                        check_ec2_utilization(cloudwatch_client, instance_id)
                    )
                else:
                    stopped_reason = instance["StateTransitionReason"]
                    stopped_time = re.findall(
                        "[0-9]{4}-[0-9]{2}-[0-9]{2}", stopped_reason
                    )
                    instance_data.append(f"stopped: {stopped_time}")

                table_data.append(instance_data)

    return table_head, table_data
