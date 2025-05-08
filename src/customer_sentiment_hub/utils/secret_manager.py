# src/customer_sentiment_hub/utils/secret_manager.py

import os
import json
import tempfile
import boto3
from botocore.exceptions import ClientError

def fetch_gemini_secret(secret_name: str, region_name: str) -> dict:
    """
    Retrieve the JSON payload stored in AWS Secrets Manager under `secret_name`.
    """
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        resp = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise

    secret_str = resp.get("SecretString")
    if not secret_str:
        raise ValueError(f"Secret {secret_name} did not contain a SecretString")

    return json.loads(secret_str)


def load_gemini_credentials(
    secret_name: str = "genai-gemini-vertex-prod-api",
    region_name: str = "us-west-1"
) -> str:
    """
    Fetches the service‑account JSON from AWS, writes it to a temp file,
    and sets the following environment variables:

      - GOOGLE_APPLICATION_CREDENTIALS
      - GOOGLE_CLOUD_PROJECT
      - GOOGLE_CLOUD_LOCATION

    Returns:
        Path to the temp JSON file.
    """
    creds = fetch_gemini_secret(secret_name, region_name)

    if "private_key" in creds and isinstance(creds["private_key"], str):
        creds["private_key"] = creds["private_key"].replace("\\n", "\n")
    # Write to a secure temp file
    fd, path = tempfile.mkstemp(prefix="gemini_creds_", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(creds, f)

    # Export for Google libraries
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
    if "project_id" in creds:
        os.environ["GOOGLE_CLOUD_PROJECT"] = creds["project_id"]
    if creds.get("location"):
        os.environ["GOOGLE_CLOUD_LOCATION"] = creds["location"]

    return path
