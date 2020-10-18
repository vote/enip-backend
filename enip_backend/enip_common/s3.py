import json
import os.path

import boto3
import botocore.config
from botocore.exceptions import ClientError

from .config import S3_BUCKET, S3_PREFIX

client_config = botocore.config.Config(max_pool_connections=50,)

s3 = boto3.client("s3", config=client_config)


def read_json(path):
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=os.path.join(S3_PREFIX, path))
    except ClientError as ex:
        if ex.response["Error"]["Code"] == "NoSuchKey":
            print("No latest file")
            return None
        else:
            raise

    return json.loads(response["Body"].read())


def write_string(path, content, content_type, acl, cache_control):
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=os.path.join(S3_PREFIX, path),
        Body=content.encode(),
        ContentType=content_type,
        ACL=acl,
        CacheControl=cache_control,
    )


def write_cacheable_json(path, content):
    write_string(
        path,
        content,
        content_type="application/json",
        acl="public-read",
        cache_control="max-age=86400",
    )


def write_noncacheable_json(path, content):
    write_string(
        path,
        content,
        content_type="application/json",
        acl="public-read",
        cache_control="no-store",
    )
