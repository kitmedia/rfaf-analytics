"""Cloudflare R2 storage service (S3-compatible via boto3).

Handles PDF upload/download and presigned URL generation.
"""

import os

import boto3
from botocore.config import Config
import structlog

logger = structlog.get_logger()

R2_ACCESS_KEY = os.getenv("CLOUDFLARE_R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.getenv("CLOUDFLARE_R2_SECRET_KEY", "")
R2_BUCKET = os.getenv("CLOUDFLARE_R2_BUCKET", "rfaf-analytics")
R2_ENDPOINT = os.getenv("CLOUDFLARE_R2_ENDPOINT", "")
R2_PUBLIC_URL = os.getenv("CLOUDFLARE_R2_PUBLIC_URL", "")

_client = None


def _get_client():
    """Lazy-init boto3 S3 client for Cloudflare R2."""
    global _client
    if _client is not None:
        return _client

    if not R2_ACCESS_KEY or not R2_ENDPOINT:
        logger.warning("r2_not_configured", hint="Set CLOUDFLARE_R2_* env vars")
        return None

    _client = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    logger.info("r2_client_initialized", endpoint=R2_ENDPOINT, bucket=R2_BUCKET)
    return _client


def upload_pdf(key: str, pdf_bytes: bytes, content_type: str = "application/pdf") -> str | None:
    """Upload PDF to R2. Returns public URL or None if R2 not configured.

    Args:
        key: Object key (e.g., 'reports/analysis-uuid.pdf')
        pdf_bytes: Raw PDF bytes
        content_type: MIME type

    Returns:
        Public URL string, or None if upload fails.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        client.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=pdf_bytes,
            ContentType=content_type,
        )

        public_url = f"{R2_PUBLIC_URL}/{key}" if R2_PUBLIC_URL else None

        logger.info(
            "r2_upload_success",
            key=key,
            size_kb=round(len(pdf_bytes) / 1024, 1),
            public_url=public_url,
        )
        return public_url

    except Exception as exc:
        logger.error("r2_upload_error", key=key, error=str(exc))
        return None


def upload_video(key: str, file_bytes: bytes, content_type: str = "video/mp4") -> str | None:
    """Upload video to R2. Returns public URL or None.

    Args:
        key: Object key (e.g., 'videos/club-uuid/video-uuid.mp4')
        file_bytes: Raw video bytes
        content_type: MIME type

    Returns:
        Public URL string, or None if upload fails.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        client.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )

        public_url = f"{R2_PUBLIC_URL}/{key}" if R2_PUBLIC_URL else None

        logger.info(
            "r2_video_upload_success",
            key=key,
            size_mb=round(len(file_bytes) / (1024 * 1024), 1),
            public_url=public_url,
        )
        return public_url

    except Exception as exc:
        logger.error("r2_video_upload_error", key=key, error=str(exc))
        return None


def download_pdf(key: str) -> bytes | None:
    """Download PDF from R2. Returns bytes or None."""
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.get_object(Bucket=R2_BUCKET, Key=key)
        data = response["Body"].read()
        logger.info("r2_download_success", key=key, size_kb=round(len(data) / 1024, 1))
        return data
    except Exception as exc:
        logger.error("r2_download_error", key=key, error=str(exc))
        return None


def generate_presigned_url(key: str, expires_in: int = 3600) -> str | None:
    """Generate presigned URL for PDF download. Expires in 1 hour by default."""
    client = _get_client()
    if client is None:
        return None

    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": R2_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
    except Exception as exc:
        logger.error("r2_presigned_error", key=key, error=str(exc))
        return None


def delete_object(key: str) -> bool:
    """Delete an object from R2."""
    client = _get_client()
    if client is None:
        return False

    try:
        client.delete_object(Bucket=R2_BUCKET, Key=key)
        logger.info("r2_delete_success", key=key)
        return True
    except Exception as exc:
        logger.error("r2_delete_error", key=key, error=str(exc))
        return False
