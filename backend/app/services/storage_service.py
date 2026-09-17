import hashlib
import uuid
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageService:
    """S3-compatible object storage service for MinIO (local) and Backblaze B2 (prod)."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        bucket_name: str | None = None,
        client: Any = None,
    ) -> None:
        self.endpoint_url = endpoint_url or settings.s3_endpoint_url
        self.bucket_name = bucket_name or settings.s3_bucket_name

        if client is not None:
            self._client = client
        else:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                config=Config(signature_version="s3v4"),
            )

    def compute_sha256(self, content: bytes) -> str:
        """Compute hexadecimal SHA-256 hash of given byte content."""
        return hashlib.sha256(content).hexdigest()

    # Alias for compatibility with callers using compute_hash
    compute_hash = compute_sha256

    def generate_storage_path(
        self, entity_id: uuid.UUID, file_hash: str, filename: str
    ) -> str:
        """Generate a secure S3 object key with path traversal characters removed."""
        safe_name = (
            filename.replace("..", "")
            .replace("/", "_")
            .replace("\\", "_")
            .lstrip("_")
        )
        if not safe_name:
            safe_name = "file"
        return f"documents/{entity_id}/{file_hash}/{safe_name}"

    def ensure_bucket_exists(self) -> None:
        """Check if bucket exists; create it if missing."""
        try:
            self._client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = str(e.response.get("Error", {}).get("Code", ""))
            http_status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if error_code in ("404", "NoSuchBucket", "NotFound") or http_status == 404:
                try:
                    self._client.create_bucket(Bucket=self.bucket_name)
                except ClientError as create_err:
                    create_code = str(
                        create_err.response.get("Error", {}).get("Code", "")
                    )
                    if create_code not in (
                        "BucketAlreadyOwnedByYou",
                        "BucketAlreadyExists",
                    ):
                        raise
            else:
                raise

    def upload_bytes(
        self,
        content: bytes,
        storage_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload raw bytes to object storage and return the storage path."""
        self._client.put_object(
            Bucket=self.bucket_name,
            Key=storage_path,
            Body=content,
            ContentType=content_type,
        )
        return storage_path

    def download_bytes(self, storage_path: str) -> bytes:
        """Download object content as raw bytes."""
        response = self._client.get_object(
            Bucket=self.bucket_name,
            Key=storage_path,
        )
        body = response["Body"]
        if hasattr(body, "read"):
            return body.read()
        if isinstance(body, bytes):
            return body
        return bytes(body)

    def delete_file(self, storage_path: str) -> None:
        """Delete an object from storage by path."""
        self._client.delete_object(
            Bucket=self.bucket_name,
            Key=storage_path,
        )
