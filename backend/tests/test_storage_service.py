import hashlib
import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.core.config import settings
from app.services.storage_service import StorageService


def test_compute_sha256() -> None:
    service = StorageService(client=MagicMock())
    empty_sha = hashlib.sha256(b"").hexdigest()
    assert service.compute_sha256(b"") == empty_sha

    data = b"Hello Greenlign Storage"
    expected_sha = hashlib.sha256(data).hexdigest()
    assert service.compute_sha256(data) == expected_sha
    assert hasattr(service, "compute_hash")
    assert service.compute_hash(data) == expected_sha


def test_generate_storage_path_standard() -> None:
    service = StorageService(client=MagicMock())
    entity_id = uuid.uuid4()
    file_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    filename = "invoice_2025.csv"

    path = service.generate_storage_path(entity_id, file_hash, filename)
    assert path == f"documents/{entity_id}/{file_hash}/invoice_2025.csv"


def test_generate_storage_path_path_traversal_removal() -> None:
    service = StorageService(client=MagicMock())
    entity_id = uuid.uuid4()
    file_hash = "abcdef123456"

    # Unix-style traversal
    path1 = service.generate_storage_path(entity_id, file_hash, "../../secret.pdf")
    assert ".." not in path1
    assert path1 == f"documents/{entity_id}/{file_hash}/secret.pdf"

    # Windows-style traversal
    path2 = service.generate_storage_path(entity_id, file_hash, r"..\..\secret.pdf")
    assert ".." not in path2
    assert "\\" not in path2
    assert path2 == f"documents/{entity_id}/{file_hash}/secret.pdf"

    # Traversal in the middle
    path3 = service.generate_storage_path(entity_id, file_hash, "folder/../../sub/document.pdf")
    assert ".." not in path3
    assert path3.startswith(f"documents/{entity_id}/{file_hash}/")
    assert path3.endswith("document.pdf")

    # Only traversal tokens
    path4 = service.generate_storage_path(entity_id, file_hash, "../..")
    assert ".." not in path4
    assert path4.startswith(f"documents/{entity_id}/{file_hash}/")
    assert not path4.endswith("/")


def test_storage_service_init_defaults() -> None:
    with patch("boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client

        service = StorageService()
        assert service.endpoint_url == settings.s3_endpoint_url
        assert service.bucket_name == settings.s3_bucket_name
        assert service._client is mock_client

        mock_boto.assert_called_once()
        args, kwargs = mock_boto.call_args
        assert args[0] == "s3"
        assert kwargs["endpoint_url"] == settings.s3_endpoint_url
        assert kwargs["aws_access_key_id"] == settings.s3_access_key
        assert kwargs["aws_secret_access_key"] == settings.s3_secret_key
        assert kwargs["config"].signature_version == "s3v4"


def test_storage_service_init_custom() -> None:
    custom_client = MagicMock()
    service = StorageService(
        endpoint_url="https://s3.us-west-004.backblazeb2.com",
        bucket_name="custom-greenlign-bucket",
        client=custom_client,
    )
    assert service.endpoint_url == "https://s3.us-west-004.backblazeb2.com"
    assert service.bucket_name == "custom-greenlign-bucket"
    assert service._client is custom_client


def test_upload_bytes_default_content_type() -> None:
    mock_client = MagicMock()
    service = StorageService(bucket_name="test-bucket", client=mock_client)
    data = b"sample content"
    target_path = "documents/123/abc/test.txt"

    result = service.upload_bytes(data, target_path)

    assert result == target_path
    mock_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key=target_path,
        Body=data,
        ContentType="application/octet-stream",
    )


def test_upload_bytes_custom_content_type() -> None:
    mock_client = MagicMock()
    service = StorageService(bucket_name="test-bucket", client=mock_client)
    data = b"%PDF-1.4 mock content"
    target_path = "documents/123/abc/bill.pdf"

    result = service.upload_bytes(data, target_path, content_type="application/pdf")

    assert result == target_path
    mock_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key=target_path,
        Body=data,
        ContentType="application/pdf",
    )


def test_download_bytes() -> None:
    mock_client = MagicMock()
    expected_data = b"downloaded file payload"
    mock_client.get_object.return_value = {"Body": io.BytesIO(expected_data)}

    service = StorageService(bucket_name="test-bucket", client=mock_client)
    target_path = "documents/123/abc/bill.pdf"

    result = service.download_bytes(target_path)

    assert result == expected_data
    mock_client.get_object.assert_called_once_with(Bucket="test-bucket", Key=target_path)


def test_delete_file() -> None:
    mock_client = MagicMock()
    service = StorageService(bucket_name="test-bucket", client=mock_client)
    target_path = "documents/123/abc/bill.pdf"

    service.delete_file(target_path)

    mock_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key=target_path)


def test_ensure_bucket_exists_when_bucket_already_exists() -> None:
    mock_client = MagicMock()
    mock_client.head_bucket.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    service = StorageService(bucket_name="test-bucket", client=mock_client)
    service.ensure_bucket_exists()

    mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")
    mock_client.create_bucket.assert_not_called()


def test_ensure_bucket_exists_creates_when_missing_404() -> None:
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
    )

    service = StorageService(bucket_name="test-bucket", client=mock_client)
    service.ensure_bucket_exists()

    mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")
    mock_client.create_bucket.assert_called_once_with(Bucket="test-bucket")


def test_ensure_bucket_exists_creates_when_missing_nosuchbucket() -> None:
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist"}},
        "HeadBucket",
    )

    service = StorageService(bucket_name="test-bucket", client=mock_client)
    service.ensure_bucket_exists()

    mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")
    mock_client.create_bucket.assert_called_once_with(Bucket="test-bucket")


def test_ensure_bucket_exists_handles_bucket_already_owned_on_create() -> None:
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
    )
    mock_client.create_bucket.side_effect = ClientError(
        {"Error": {"Code": "BucketAlreadyOwnedByYou"}}, "CreateBucket"
    )

    service = StorageService(bucket_name="test-bucket", client=mock_client)
    service.ensure_bucket_exists()

    mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")
    mock_client.create_bucket.assert_called_once_with(Bucket="test-bucket")


def test_ensure_bucket_exists_reraises_other_head_errors() -> None:
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadBucket"
    )

    service = StorageService(bucket_name="test-bucket", client=mock_client)
    with pytest.raises(ClientError) as exc_info:
        service.ensure_bucket_exists()

    assert exc_info.value.response["Error"]["Code"] == "403"
    mock_client.create_bucket.assert_not_called()


def test_ensure_bucket_exists_reraises_unexpected_create_errors() -> None:
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
    )
    mock_client.create_bucket.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "CreateBucket"
    )

    service = StorageService(bucket_name="test-bucket", client=mock_client)
    with pytest.raises(ClientError) as exc_info:
        service.ensure_bucket_exists()

    assert exc_info.value.response["Error"]["Code"] == "AccessDenied"
