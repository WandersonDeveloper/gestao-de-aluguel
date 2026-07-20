import uuid

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config.settings import settings

_client = None
_public_client = None


def get_s3_client():
    """Cliente para chamadas internas (backend -> MinIO), via hostname da rede Docker."""
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
        )
    return _client


def _get_public_s3_client():
    """Cliente usado só para gerar presigned URLs — precisa do endpoint que o
    navegador/cliente externo consegue resolver, que é diferente do endpoint
    interno usado pelo backend para falar com o MinIO dentro da rede Docker."""
    global _public_client
    if _public_client is None:
        _public_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_public_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
        )
    return _public_client


def ensure_bucket_exists() -> None:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket_name)
    except ClientError:
        client.create_bucket(Bucket=settings.s3_bucket_name)


def upload_file(file_bytes: bytes, filename: str, content_type: str | None) -> str:
    extension = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    key = f"{uuid.uuid4()}.{extension}"
    get_s3_client().put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=file_bytes,
        ContentType=content_type or "application/octet-stream",
    )
    return key


def delete_file(key: str) -> None:
    get_s3_client().delete_object(Bucket=settings.s3_bucket_name, Key=key)


def get_file_url(key: str, expires_in: int = 3600) -> str:
    return _get_public_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": key},
        ExpiresIn=expires_in,
    )
