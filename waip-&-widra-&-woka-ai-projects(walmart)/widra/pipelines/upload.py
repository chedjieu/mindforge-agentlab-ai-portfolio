"""Object store adapter — MinIO/S3 with local filesystem fallback."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from app.config import get_settings

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
LOCAL_OBJECTS = ROOT / "data" / "local_store" / "objects"


class ObjectStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        self.backend = "local"
        self._init_client()

    def _init_client(self) -> None:
        try:
            import boto3
            from botocore.client import Config

            client = boto3.client(
                "s3",
                endpoint_url=self.settings.s3_endpoint,
                aws_access_key_id=self.settings.s3_access_key,
                aws_secret_access_key=self.settings.s3_secret_key,
                config=Config(signature_version="s3v4"),
                region_name="us-east-1",
            )
            client.list_buckets()
            bucket = self.settings.s3_bucket
            existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
            if bucket not in existing:
                client.create_bucket(Bucket=bucket)
            self._client = client
            self.backend = "s3"
            logger.info("ObjectStore using S3/MinIO at %s", self.settings.s3_endpoint)
        except Exception as exc:  # noqa: BLE001
            logger.warning("S3 unavailable (%s); using local object store", exc)
            LOCAL_OBJECTS.mkdir(parents=True, exist_ok=True)
            self._client = None
            self.backend = "local"

    def upload(self, path: Path, *, doc_id: str | None = None, version: int = 1) -> str:
        path = Path(path)
        doc_id = doc_id or str(uuid4())
        key = f"docs/{doc_id}/v{version}/source.pdf"
        data = path.read_bytes()

        if self.backend == "s3" and self._client is not None:
            self._client.put_object(
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=data,
                ContentType="application/pdf",
            )
            return key

        dest = LOCAL_OBJECTS / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return key


def upload_pdf(path: Path, *, doc_id: str | None = None, version: int = 1) -> str:
    return ObjectStore().upload(path, doc_id=doc_id, version=version)
