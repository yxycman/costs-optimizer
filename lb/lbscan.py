#!/usr/bin/env python3
"""
Load Balancer scanner
"""
import re
from datetime import datetime, timedelta
import boto3
from pricing.price import get_load_balancer_price

SESSION = boto3.Session()
END_TIME = datetime.now()
START_TIME = END_TIME - timedelta(days=30)
INSTANCE_PRICE_MAP = {}


def check_lb_utilization(
    cloudwatch_client, dimension_name, metric_name, namespace, lb_name
):
    """
    LB utilization check
    """
    response = cloudwatch_client.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=[
            {"Name": dimension_name, "Value": lb_name},
        ],
        StartTime=START_TIME,
        EndTime=END_TIME,
        Period=3600,
        Statistics=["Sum"],
    )

    data_points = response["Datapoints"]
    total_usage = sum(data_point["Sum"] for data_point in data_points)
    if len(data_points):
        average_usage = total_usage / len(data_points)
        max_usage = max(data_point["Sum"] for data_point in data_points)
        min_usage = min(data_point["Sum"] for data_point in data_points)
    else:
        average_usage = 0
        max_usage = 0
        min_usage = 0

    return f"AVG: {int(average_usage)}, MAX: {int(max_usage)}, MIN: {int(min_usage)}"


def query_lb(region):
    """
    LB entrypoint
    """
    # pylint: disable=too-many-locals,too-many-branches
    elbv1_client = SESSION.client("elb", region_name=region)
    elbv2_client = SESSION.client("elbv2", region_name=region)
    cloudwatch_client = SESSION.client("cloudwatch", region_name=region)

    paginator_v1 = elbv1_client.get_paginator("describe_load_balancers")
    page_iterator_v1 = paginator_v1.paginate()
    paginator_v2 = elbv2_client.get_paginator("describe_load_balancers")
    page_iterator_v2 = paginator_v2.paginate()

    table_head = [
        "LoadBalancerId",
        "Name (crop 20)",
        "Type",
        "30 days RequestCount/ActiveConnectionCount",
        "Monthly hour cost",
    ]
    table_data = []

    print(f"\n\n✨  Running in Load Balancer V1 mode {region}")
    lbv1_price = get_load_balancer_price(INSTANCE_PRICE_MAP, region, "classic")
    for page in page_iterator_v1:
        for lb in page["LoadBalancerDescriptions"]:
            lb_type = "classic"
            lb_name = lb["LoadBalancerName"]
            lb_data = check_lb_utilization(
                cloudwatch_client,
                "LoadBalancerName",
                "RequestCount",
                "AWS/ELB",
                lb_name,
            )
            table_data.append([lb_name, lb_name, lb_type, lb_data, lbv1_price])

    print(f"✨  Running in Load Balancer V2 mode {region}")
    lbv2_price = get_load_balancer_price(INSTANCE_PRICE_MAP, region, "application")
    for page in page_iterator_v2:
        for lb in page["LoadBalancers"]:
            lb_type = lb["Type"]
            lb_name = lb["LoadBalancerName"]
            lb_arn = lb["LoadBalancerArn"]
            lb_id = re.sub(r".*loadbalancer/", "", lb_arn)
            lb_data = check_lb_utilization(
                cloudwatch_client,
                "LoadBalancer",
                "ActiveConnectionCount",
                "AWS/ApplicationELB",
                lb_id,
            )
            table_data.append([lb_id, lb_name, lb_type, lb_data, lbv2_price])

    return table_head, table_data
