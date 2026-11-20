import os
import sys

import boto3
from botocore.config import Config

bucket = "mlflow-artifacts"
expected = b"MinIO J2 : donnees conservees"

if len(sys.argv) != 2 or sys.argv[1] not in {"write", "read"}:
    raise SystemExit("Usage: verifier-s3.py write|read")

key = os.environ["J2_OBJECT_KEY"]
s3 = boto3.client(
    "s3",
    endpoint_url="http://minio:9000",
    aws_access_key_id=os.environ["MINIO_ROOT_USER"],
    aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
    region_name="us-east-1",
    config=Config(s3={"addressing_style": "path"}),
)

if sys.argv[1] == "write":
    buckets = {item["Name"] for item in s3.list_buckets()["Buckets"]}
    if bucket not in buckets:
        s3.create_bucket(Bucket=bucket)
    s3.put_object(Bucket=bucket, Key=key, Body=expected)
    print(f"Written: s3://{bucket}/{key}")
else:
    response = s3.get_object(Bucket=bucket, Key=key)
    body = response["Body"]
    try:
        actual = body.read()
    finally:
        body.close()
    if actual != expected:
        raise SystemExit("The S3 object does not match the written content.")
    print(actual.decode())
