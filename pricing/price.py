#!/usr/bin/env python3
"""
Pricing functions
"""
import re
import json
import boto3


SESSION = boto3.Session()


def engine_filter(resource_filter, instance_engine):
    """
    Filter by engine
    """
    if instance_engine == "aurora-postgresql":
        resource_filter.append(
            {
                "Type": "TERM_MATCH",
                "Field": "databaseEngine",
                "Value": "Aurora PostgreSQL",
            }
        )
    elif instance_engine == "aurora-mysql":
        resource_filter.append(
            {
                "Type": "TERM_MATCH",
                "Field": "databaseEngine",
                "Value": "Aurora MySQL",
            }
        )
    elif instance_engine == "mariadb":
        resource_filter.append(
            {
                "Type": "TERM_MATCH",
                "Field": "databaseEngine",
                "Value": "MariaDB",
            }
        )


def az_filter(resource_filter, instance_az):
    """
    Filter by AZ
    """
    if instance_az:
        resource_filter.append(
            {"Field": "deploymentOption", "Value": "Multi-AZ", "Type": "TERM_MATCH"}
        )
    else:
        resource_filter.append(
            {
                "Field": "deploymentOption",
                "Value": "Single-AZ",
                "Type": "TERM_MATCH",
            }
        )


def storage_filter(resource_filter, instance_storage):
    """
    Filter by storage
    """
    if instance_storage in ["aurora", "gp2"]:
        resource_filter.append(
            {"Type": "TERM_MATCH", "Field": "storage", "Value": "EBS Only"}
        )
    elif instance_storage == "aurora-iopt1":
        resource_filter.append(
            {
                "Type": "TERM_MATCH",
                "Field": "storage",
                "Value": "Aurora IO Optimization Mode",
            }
        )


def serverless_filter(resource_filter, instance_class, instance_storage, instance_az):
    """
    Filter if SL
    """
    if instance_class == "db.serverless":
        mp_factor = 1
        resource_filter.append(
            {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Serverless"}
        )
    else:
        mp_factor = 730
        resource_filter.append(
            {"Field": "instanceType", "Value": instance_class, "Type": "TERM_MATCH"}
        )
        # storage filter
        storage_filter(resource_filter, instance_storage)
        # az filter
        az_filter(resource_filter, instance_az)

    return mp_factor


def calculate_on_demand(data, mp_factor):
    """
    Calculate On-Demand price
    """

    if data.get("PriceList"):
        od = json.loads(data["PriceList"][0])["terms"]["OnDemand"]
        id1 = list(od)[0]
        id2 = list(od[id1]["priceDimensions"])[0]

        monthly_cost = (
            float(od[id1]["priceDimensions"][id2]["pricePerUnit"]["USD"]) * mp_factor
        )
    else:
        return "UNKN"

    return round(monthly_cost, 3)


def get_rds_price(price_map, instance_config_map, region):
    """
    RDS cost query
    """
    cost_id = (
        region
        + instance_config_map["instance_class"]
        + instance_config_map["instance_storage"]
        + str(instance_config_map["instance_az"])
    )
    if cost_id in price_map.keys():
        monthly_cost = price_map[cost_id]
    else:
        client = SESSION.client("pricing", region_name="us-east-1")
        resource_filter = [
            {"Field": "regionCode", "Value": region, "Type": "TERM_MATCH"}
        ]
        # engine filter
        engine_filter(resource_filter, instance_config_map["instance_engine"])

        # serverless filter
        mp_factor = serverless_filter(
            resource_filter,
            instance_config_map["instance_class"],
            instance_config_map["instance_storage"],
            instance_config_map["instance_az"],
        )

        data = client.get_products(ServiceCode="AmazonRDS", Filters=resource_filter)
        if len(data["PriceList"]) > 1:
            return "MULT"
        monthly_cost = calculate_on_demand(data, mp_factor)
        price_map[cost_id] = monthly_cost

    return monthly_cost


def get_ebs_price(price_map, volume_type, region):
    """
    EBS cost query
    """
    cost_id = region + volume_type
    if cost_id in price_map.keys():
        monthly_cost = price_map[cost_id]
    else:
        client = SESSION.client("pricing", region_name="us-east-1")
        resource_filter = [
            {"Field": "volumeApiName", "Value": volume_type, "Type": "TERM_MATCH"},
            {"Field": "productFamily", "Value": "Storage", "Type": "TERM_MATCH"},
            {"Field": "regionCode", "Value": region, "Type": "TERM_MATCH"},
        ]

        data = client.get_products(ServiceCode="AmazonEC2", Filters=resource_filter)
        if len(data["PriceList"]) > 1:
            return "MULT"
        monthly_cost = calculate_on_demand(data, 1)
        price_map[cost_id] = monthly_cost

    return monthly_cost


def get_ec2_price(price_map, instance, os, region):
    """
    EC2 instances cost query
    """
    cost_id = instance + os
    if cost_id in price_map.keys():
        monthly_cost = price_map[cost_id]
    else:
        client = SESSION.client("pricing", region_name="us-east-1")
        resource_filter = [
            {"Field": "tenancy", "Value": "shared", "Type": "TERM_MATCH"},
            {"Field": "operatingSystem", "Value": os, "Type": "TERM_MATCH"},
            {"Field": "preInstalledSw", "Value": "NA", "Type": "TERM_MATCH"},
            {"Field": "instanceType", "Value": instance, "Type": "TERM_MATCH"},
            {"Field": "regionCode", "Value": region, "Type": "TERM_MATCH"},
            {"Field": "capacitystatus", "Value": "Used", "Type": "TERM_MATCH"},
        ]

        if os == "Windows":
            resource_filter.append(
                {
                    "Field": "licenseModel",
                    "Value": "No License required",
                    "Type": "TERM_MATCH",
                }
            )

        data = client.get_products(ServiceCode="AmazonEC2", Filters=resource_filter)
        if len(data["PriceList"]) > 1:
            return "MULT"
        monthly_cost = calculate_on_demand(data, 730)
        price_map[cost_id] = monthly_cost

    return monthly_cost


def get_snapshot_price(snapshot_price, snapshot_tier, snapshot_size, region):
    """
    EC2 snapshots cost query
    """

    gb_cost = "UNKN"
    monthly_cost = "UNKN"

    if snapshot_tier in snapshot_price.keys():
        gb_cost = snapshot_price[snapshot_tier]
        monthly_cost = gb_cost * snapshot_size
        return gb_cost, monthly_cost

    if snapshot_tier not in ["archive", "standard"]:
        return gb_cost, monthly_cost

    client = SESSION.client("pricing", region_name="us-east-1")

    resource_filter = [
        {"Field": "productFamily", "Value": "Storage Snapshot", "Type": "TERM_MATCH"},
        {"Field": "regionCode", "Value": region, "Type": "TERM_MATCH"},
    ]

    data = client.get_products(ServiceCode="AmazonEC2", Filters=resource_filter)

    usagetype = (
        "SnapshotArchiveStorage" if snapshot_tier == "archive" else "SnapshotUsage"
    )

    for unit in data["PriceList"]:
        unit = json.loads(unit)
        od = unit["terms"]["OnDemand"]
        id1 = list(od)[0]
        id2 = list(od[id1]["priceDimensions"])[0]

        if re.match(f".*{usagetype}$", unit["product"]["attributes"]["usagetype"]):
            gb_cost = float(od[id1]["priceDimensions"][id2]["pricePerUnit"]["USD"])
            snapshot_price[snapshot_tier] = gb_cost
            monthly_cost = gb_cost * snapshot_size

    return gb_cost, monthly_cost


def get_load_balancer_price(price_map, region, lb_type):
    """
    Load Balancer cost query
    """
    cost_id = region + lb_type
    if cost_id in price_map.keys():
        monthly_cost = price_map[cost_id]
    else:
        client = SESSION.client("pricing", region_name="us-east-1")

        resource_filter = [
            {"Field": "regionCode", "Value": region, "Type": "TERM_MATCH"},
            {"Field": "productFamily", "Value": "Load Balancer", "Type": "TERM_MATCH"},
        ]

        data = client.get_products(ServiceCode="AmazonEC2", Filters=resource_filter)
        monthly_cost = "UNKN"
        for price_item in data["PriceList"]:
            unit = json.loads(price_item)
            usage_type = unit["product"]["attributes"]["usagetype"]
            if re.match(f".*LoadBalancerUsage", usage_type):
                od = unit["terms"]["OnDemand"]
                id1 = list(od)[0]
                id2 = list(od[id1]["priceDimensions"])[0]
                monthly_cost = 730 * float(
                    od[id1]["priceDimensions"][id2]["pricePerUnit"]["USD"]
                )
                return monthly_cost

    return monthly_cost


def get_log_group_storage_costs(price_map, region):
    """
    Log group storage costs query
    """
    cost_id = region
    if cost_id in price_map.keys():
        monthly_cost = price_map[cost_id]
    else:
        client = SESSION.client("pricing", region_name="us-east-1")
        resource_filter = [
            {"Field": "regionCode", "Value": region, "Type": "TERM_MATCH"},
            {
                "Field": "productFamily",
                "Value": "Storage Snapshot",
                "Type": "TERM_MATCH",
            },
        ]

        data = client.get_products(
            ServiceCode="AmazonCloudWatch", Filters=resource_filter
        )
        monthly_cost = "UNKN"
        for price_item in data["PriceList"]:
            unit = json.loads(price_item)
            usage_type = unit["product"]["attributes"]["usagetype"]
            if re.match(f".*TimedStorage-ByteHrs", usage_type):
                od = unit["terms"]["OnDemand"]
                id1 = list(od)[0]
                id2 = list(od[id1]["priceDimensions"])[0]
                monthly_cost = float(
                    od[id1]["priceDimensions"][id2]["pricePerUnit"]["USD"]
                )
                return monthly_cost

    return monthly_cost
