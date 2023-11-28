from minio import Minio
import validators
import pytest

@pytest.mark.UNIT
@pytest.mark.API
def test_make_bucket(minio_mock):
    bucket_name = "test-bucket"
    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    assert client.bucket_exists(bucket_name), "Bucket should exist after creation"

@pytest.mark.UNIT
@pytest.mark.API
def test_adding_and_removing_objects(minio_mock):
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_path = "fixtures/maya.jpeg"

    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    client.make_bucket(bucket_name)
    client.fput_object(bucket_name, object_name, file_path)

    assert object_name in client.buckets[bucket_name], "Object should be in the bucket after upload"
    client.remove_object(bucket_name, object_name)
    
    assert object_name not in client.buckets[bucket_name]

@pytest.mark.UNIT
@pytest.mark.API
def test_file_download(minio_mock):
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_content = b"Test file content"

    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    client.put_object(bucket_name, object_name, file_content)

    response = client.get_object(bucket_name, object_name)
    downloaded_content = response.data

    assert downloaded_content == file_content, "Downloaded content should match the original"

@pytest.mark.UNIT
@pytest.mark.API
def test_bucket_exists(minio_mock):
    bucket_name = "existing-bucket"
    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    assert client.bucket_exists(bucket_name), "Bucket should exist"


@pytest.mark.UNIT
@pytest.mark.API
def test_get_presigned_url(minio_mock):
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_path = "fixtures/maya.jpeg"

    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    client.make_bucket(bucket_name)
    client.fput_object(bucket_name, object_name, file_path)
    url = client.get_presigned_url(
        "GET",
        bucket_name,
        object_name
    )
    assert validators.url(url)


@pytest.mark.UNIT
@pytest.mark.API
def test_list_buckets(minio_mock):
    client = Minio("http://local.host:9000")
    buckets = client.list_buckets()
    n = len(buckets)
    bucket_name = "new-bucket"
    client.make_bucket(bucket_name)
    buckets = client.list_buckets()
    assert len(buckets)==n+1