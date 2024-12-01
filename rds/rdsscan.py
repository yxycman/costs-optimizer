#!/usr/bin/env python3

import re
from datetime import datetime, timedelta
import boto3
from pricing.price import get_rds_price

SESSION = boto3.Session()
RDS_PRICE_MAP = {}
AVAILABLE_INSTANCE_TYPES = set()
END_TIME = datetime.now()
START_TIME = END_TIME - timedelta(days=30)


def check_instance_type(client, cluster_engine, recommended_instance):
    """
    RDS type existence
    """
    result = False

    if recommended_instance not in AVAILABLE_INSTANCE_TYPES:
        describe_result = client.describe_orderable_db_instance_options(
            Engine=cluster_engine, DBInstanceClass=recommended_instance
        )
        if describe_result["OrderableDBInstanceOptions"]:
            result = True
    else:
        result = True

    return result


def check_recommendation(client, cluster_engine, instance_class):
    """
    RDS recommendation check
    """
    instance_kind = instance_class.split(".")[1]
    instance_size = instance_class.split(".")[2]
    instance_type = instance_kind[0]
    instance_generation = instance_kind[1::]
    instance_recommendation = False

    if re.match("^t", instance_type):
        if instance_generation in ["2", "3"]:
            recommended_instance = f"db.{instance_type}"
            recommended_instance += f"4g.{instance_size}"
            if (
                check_instance_type(client, cluster_engine, recommended_instance)
                and recommended_instance != instance_class
            ):
                AVAILABLE_INSTANCE_TYPES.add(recommended_instance)
                instance_recommendation = recommended_instance

    elif re.match("^m|^r", instance_type):
        if re.match("^2|^3|^4|^5|^6", instance_generation):
            recommended_instance = f"db.{instance_type}"
            recommended_instance += f"6g.{instance_size}"
            if (
                check_instance_type(client, cluster_engine, recommended_instance)
                and recommended_instance != instance_class
            ):
                AVAILABLE_INSTANCE_TYPES.add(recommended_instance)
                instance_recommendation = recommended_instance

    return instance_recommendation


def check_rds_connection(cloudwatch_client, instance_id):
    """
    RDS connections check
    """
    response = cloudwatch_client.get_metric_statistics(
        Namespace="AWS/RDS",
        MetricName="DatabaseConnections",
        Dimensions=[
            {"Name": "DBInstanceIdentifier", "Value": instance_id},
        ],
        StartTime=START_TIME,
        EndTime=END_TIME,
        Period=3600,
        Statistics=["Maximum"],
    )

    data_points = response["Datapoints"]
    if len(data_points):
        max_usage = max(data_point["Maximum"] for data_point in data_points)
    else:
        max_usage = 0

    return int(max_usage)


def check_rds_utilization(cloudwatch_client, instance_id):
    """
    RDS utilization check
    """
    response = cloudwatch_client.get_metric_statistics(
        Namespace="AWS/RDS",
        MetricName="CPUUtilization",
        Dimensions=[
            {"Name": "DBInstanceIdentifier", "Value": instance_id},
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


def query_rds(ai, region):
    """
    RDS entry point
    """
    print(f"\nRunning in RDS mode {region}")

    client = SESSION.client("rds", region_name=region)
    cloudwatch_client = SESSION.client("cloudwatch", region_name=region)

    c_paginator = client.get_paginator("describe_db_clusters")
    c_page_iterator = c_paginator.paginate()
    i_paginator = client.get_paginator("describe_db_instances")
    i_page_iterator = i_paginator.paginate()

    table_head = [
        "ClusterId (crop 20)",
        "Writer",
        "InstanceId (crop 20)",
        "MultiAZ",
        "Engine",
        "Engine Version",
        "Current",
        "Future",
        "30 days CPU load",
        "Connections",
    ]
    table_data = []
    clustered_instances = {}

    for page in c_page_iterator:
        for cluster in page["DBClusters"]:
            cluster_id = cluster["DBClusterIdentifier"]
            cluster_members = cluster["DBClusterMembers"]

            for cluster_member in cluster_members:
                instance_id = cluster_member["DBInstanceIdentifier"]
                instance_writer = cluster_member["IsClusterWriter"]

                clustered_instances[instance_id] = {
                    "id": cluster_id,
                    "is_writer": instance_writer,
                }

    for page in i_page_iterator:
        for instance in page["DBInstances"]:
            instance_id = instance["DBInstanceIdentifier"]
            instance_engine = instance["Engine"]
            instance_engine_version = instance["EngineVersion"]
            instance_class = instance["DBInstanceClass"]

            instance_class = instance["DBInstanceClass"]
            instance_storage = instance["StorageType"]
            instance_status = instance["DBInstanceStatus"]
            instance_az = instance["MultiAZ"]

            instance_config_map = {
                "instance_engine": instance_engine,
                "instance_class": instance_class,
                "instance_storage": instance_storage,
                "instance_az": instance_az,
            }

            in_cluster = clustered_instances.get(instance_id)
            if in_cluster:
                cluster_member = in_cluster["id"]
                cluster_writer = in_cluster["is_writer"]
                cluster_data = [
                    cluster_member[-20::],
                    cluster_writer,
                ]
            else:
                cluster_data = ["N/A", "N/A"]

            cluster_data.append(instance_id[-20::])
            cluster_data.append(instance_az)
            cluster_data.append(instance_engine)
            cluster_data.append(instance_engine_version)

            current_node_price = get_rds_price(
                RDS_PRICE_MAP,
                instance_config_map,
                region,
            )
            if instance_class == "db.serverless":
                current_node_price = f"{current_node_price}/1ACU"
                cluster_data.append(current_node_price)
                cluster_data.append("N/A")
            else:
                cluster_data.append(f"{instance_class} {current_node_price}$")
                instance_replacement = check_recommendation(
                    client, instance_engine, instance_class
                )
                if instance_replacement:
                    instance_config_map["instance_class"] = instance_replacement
                    future_node_price = get_rds_price(
                        RDS_PRICE_MAP,
                        instance_config_map,
                        region,
                    )
                    if isinstance(current_node_price, str) or isinstance(
                        future_node_price, str
                    ):
                        cluster_data.append("N/A")
                    else:
                        saving = round((current_node_price - future_node_price), 2)
                        cluster_data.append(
                            f"{instance_replacement} {future_node_price}$ (save:{saving}$)"
                        )
                else:
                    cluster_data.append("N/A")

            if instance_status == "available":
                cluster_data.append(
                    check_rds_utilization(cloudwatch_client, instance_id)
                )
                connections = check_rds_connection(cloudwatch_client, instance_id)
                if connections == 0:
                    cluster_data[6] = f"delete node (save:{current_node_price}$)"
                cluster_data.append(connections)
            else:
                cluster_data.append(instance_status)
                cluster_data.append(instance_status)

            table_data.append(cluster_data)

    return table_head, table_data
