#!/usr/bin/env python3
"""Backup PostgreSQL to Cloudflare R2 (S3-compatible).

Usage:
    python backend/scripts/backup_postgres.py

Requires: pg_dump available in PATH, env vars for R2 configured.
Can be scheduled via Celery beat or cron.
"""

import gzip
import os
import subprocess
import sys
from datetime import datetime

import boto3
import structlog

sys.path.insert(0, ".")

logger = structlog.get_logger()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://rfaf_user:rfaf_pass@localhost:5432/rfaf_analytics",
)
R2_ACCESS_KEY = os.getenv("CLOUDFLARE_R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.getenv("CLOUDFLARE_R2_SECRET_KEY", "")
R2_ENDPOINT = os.getenv("CLOUDFLARE_R2_ENDPOINT", "")
R2_BUCKET = os.getenv("CLOUDFLARE_R2_BUCKET", "rfaf-analytics")


def _parse_db_url(url: str) -> dict:
    """Extract host, port, user, password, dbname from DATABASE_URL."""
    # postgresql+asyncpg://user:pass@host:port/dbname
    url = url.split("://", 1)[1]  # remove scheme
    userpass, hostdb = url.split("@", 1)
    user, password = userpass.split(":", 1)
    hostport, dbname = hostdb.split("/", 1)
    if ":" in hostport:
        host, port = hostport.split(":", 1)
    else:
        host, port = hostport, "5432"
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "dbname": dbname,
    }


def backup_postgres() -> str | None:
    """Run pg_dump, compress with gzip, upload to R2.

    Returns the R2 key of the backup, or None on failure.
    """
    db = _parse_db_url(DATABASE_URL)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{db['dbname']}_{timestamp}.sql.gz"
    local_path = f"/tmp/{filename}"

    logger.info("backup_start", database=db["dbname"], host=db["host"])

    # pg_dump
    env = os.environ.copy()
    env["PGPASSWORD"] = db["password"]

    try:
        result = subprocess.run(
            [
                "pg_dump",
                "-h", db["host"],
                "-p", db["port"],
                "-U", db["user"],
                "-d", db["dbname"],
                "--no-owner",
                "--no-acl",
            ],
            capture_output=True,
            env=env,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error("pg_dump_failed", stderr=result.stderr.decode()[:500])
            return None
    except FileNotFoundError:
        logger.error("pg_dump_not_found", msg="pg_dump no disponible en PATH")
        return None

    # Compress
    with gzip.open(local_path, "wb") as f:
        f.write(result.stdout)

    size_mb = os.path.getsize(local_path) / (1024 * 1024)
    logger.info("backup_compressed", path=local_path, size_mb=round(size_mb, 2))

    # Upload to R2
    if not R2_ACCESS_KEY or not R2_ENDPOINT:
        logger.warn("r2_not_configured", msg="Backup guardado solo localmente")
        print(f"Backup local: {local_path} ({size_mb:.2f} MB)")
        return local_path

    r2_key = f"backups/{filename}"

    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
        )
        s3.upload_file(local_path, R2_BUCKET, r2_key)
        logger.info("backup_uploaded", bucket=R2_BUCKET, key=r2_key, size_mb=round(size_mb, 2))
        print(f"Backup subido: s3://{R2_BUCKET}/{r2_key} ({size_mb:.2f} MB)")
    except Exception as e:
        logger.error("r2_upload_failed", error=str(e))
        print(f"Error subiendo a R2: {e}")
        print(f"Backup local disponible: {local_path}")
        return local_path

    # Clean local file
    os.remove(local_path)
    return r2_key


if __name__ == "__main__":
    backup_postgres()
