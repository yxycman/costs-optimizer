#!/usr/bin/env python3
"""
ECR Images scanner
"""
from datetime import datetime, timezone, timedelta
import boto3


SESSION = boto3.Session()


def process_repository(ecr_client, repo_name, table_data):
    # pylint: disable=too-many-locals,too-many-branches
    """
    Process a repository and get vulnerability findings for the most recent image
    """
    print(f"Processing repository: {repo_name}")

    six_month_ago = datetime.now(timezone.utc) - timedelta(days=180)
    images_paginator = ecr_client.get_paginator("describe_images")
    images_page_iterator = images_paginator.paginate(repositoryName=repo_name)

    for page in images_page_iterator:
        images = page.get("imageDetails", [])

        for image in images:
            image_digest = image.get("imageDigest")
            image_tags = image.get("imageTags", [])
            image_pushed_at = image.get("imagePushedAt")
            image_last_pulled = image.get("lastRecordedPullTime")
            image_size_in_bytes = image.get("imageSizeInBytes")
            if image_size_in_bytes:
                image_size_in_megabytes = image_size_in_bytes / (1000 * 1000)
            else:
                image_size_in_megabytes = "N/A"

            if not image_last_pulled or image_last_pulled <= six_month_ago:
                table_data.append(
                    [
                        repo_name,
                        image_digest,
                        str(image_tags),
                        str(image_pushed_at),
                        str(image_last_pulled),
                        int(image_size_in_megabytes),
                    ]
                )

    return table_data


def query_ecr_images(region):
    """
    ECR Images entrypoint
    """
    print(
        f"\n\n✨  Running in ECR Images mode {region} for images not used within 90 days"
    )

    ecr_client = SESSION.client("ecr", region_name=region)
    paginator = ecr_client.get_paginator("describe_repositories")
    page_iterator = paginator.paginate()

    table_head = [
        "Repo name",
        "Image digest",
        "Image tags",
        "Image pushed at",
        "Image last pulled",
        "MB",
    ]
    table_data = []

    for page in page_iterator:
        for repo in page["repositories"]:
            repo_name = repo["repositoryName"]
            process_repository(ecr_client, repo_name, table_data)

    return table_head, table_data
