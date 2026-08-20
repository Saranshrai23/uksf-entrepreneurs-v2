import os

import boto3


S3_BUCKET = os.environ["S3_BUCKET"]
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION
)


def upload_file(file, key, content_type):
    s3.upload_fileobj(
        file,
        S3_BUCKET,
        key,
        ExtraArgs={
            "ContentType": content_type
        }
    )
    return key


def upload_bytes(data, key, content_type):
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type
    )
    return key


def get_file_url(key):
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": S3_BUCKET,
            "Key": key
        },
        ExpiresIn=3600
    )
