from __future__ import annotations

import io
from dataclasses import dataclass

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    key: str
    size: int
    etag: str | None = None


class ObjectStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.evidence_bucket = settings.minio_evidence_bucket
        self.report_bucket = settings.minio_report_bucket

    def ensure_buckets(self) -> None:
        for bucket in (self.evidence_bucket, self.report_bucket):
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)

    def exists(self, bucket: str, key: str) -> bool:
        try:
            self.client.stat_object(bucket, key)
            return True
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                return False
            raise

    def put_bytes(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        prevent_overwrite: bool = True,
    ) -> StoredObject:
        if prevent_overwrite and self.exists(bucket, key):
            raise FileExistsError(f"Object already exists: {bucket}/{key}")

        result = self.client.put_object(
            bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return StoredObject(bucket=bucket, key=key, size=len(data), etag=result.etag)

    def get_bytes(self, bucket: str, key: str) -> bytes:
        response = self.client.get_object(bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()


storage = ObjectStorage()
