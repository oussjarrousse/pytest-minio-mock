import os
import sys

import pytest
import validators
from minio import Minio
from minio.commonconfig import ENABLED
from minio.datatypes import Bucket
from minio.datatypes import Object
from minio.error import S3Error
from minio.versioningconfig import OFF
from minio.versioningconfig import SUSPENDED
from minio.versioningconfig import VersioningConfig

from pytest_minio_mock.plugin import MockMinioBucket
from pytest_minio_mock.plugin import MockMinioObject


@pytest.mark.UNIT
class TestsMockMinioObject:
    @pytest.mark.UNIT
    def test_mock_minio_object_init(self):
        mock_minio_object = MockMinioObject("test-bucket", "test-object")
        assert mock_minio_object.versions == {}


@pytest.mark.UNIT
class TestsMockMinioBucket:
    @pytest.mark.UNIT
    def test_mock_minio_bucket_init(self):
        mock_minio_bucket = MockMinioBucket(
            bucket_name="test-bucket", versioning=VersioningConfig()
        )
        assert mock_minio_bucket.bucket_name == "test-bucket"
        assert mock_minio_bucket.versioning.status == OFF
        assert mock_minio_bucket.objects == {}

        versioning_config = VersioningConfig(ENABLED)
        mock_minio_bucket = MockMinioBucket(
            bucket_name="test-bucket", versioning=versioning_config
        )
        assert isinstance(mock_minio_bucket._versioning, VersioningConfig)
        assert mock_minio_bucket.versioning.status == ENABLED

    @pytest.mark.UNIT
    def test_versioning(self):
        mock_minio_bucket = MockMinioBucket(
            bucket_name="test-bucket", versioning=VersioningConfig()
        )
        versioning_config = mock_minio_bucket.versioning
        assert isinstance(versioning_config, VersioningConfig)
        assert versioning_config.status == OFF
        versioning_config = VersioningConfig(status=ENABLED)
        mock_minio_bucket.versioning = versioning_config
        versioning_config = mock_minio_bucket.versioning
        assert isinstance(versioning_config, VersioningConfig)
        assert versioning_config.status == ENABLED


@pytest.mark.UNIT
@pytest.mark.API
def test_make_bucket(minio_mock):
    bucket_name = "test-bucket"
    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    assert client.bucket_exists(bucket_name), "Bucket should exist after creation"


@pytest.mark.UNIT
@pytest.mark.API
def test_remove_bucket(minio_mock):
    client = Minio("http://local.host:9000")
    original_buckets = client.list_buckets()
    n = len(original_buckets)
    bucket_name = "new-bucket"
    client.make_bucket(bucket_name)
    buckets = client.list_buckets()
    assert len(buckets) == n + 1
    client.remove_bucket(bucket_name)
    buckets = client.list_buckets()
    assert buckets == original_buckets


@pytest.mark.API
@pytest.mark.FUNC
def test_putting_and_removing_objects_no_versionning(minio_mock):
    # simple thing
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_path = "tests/fixtures/maya.jpeg"

    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    client.fput_object(bucket_name, object_name, file_path)

    assert (
        object_name in client.buckets[bucket_name].objects
    ), "Object should be in the bucket after upload"
    objects = list(client.list_objects(bucket_name))
    assert len(objects) == 1
    client.remove_object(bucket_name, object_name)
    assert object_name not in client.buckets[bucket_name].objects
    objects = list(client.list_objects(bucket_name))
    assert len(objects) == 0

    # even if include version is True nothing should change because versioning is OFF
    objects = list(client.list_objects(bucket_name, include_version=True))
    assert len(objects) == 0

    # test retrieving object after it has been removed
    with pytest.raises(S3Error) as error:
        _ = client.get_object(bucket_name, object_name)
    assert "The specified key does not exist" in str(error.value)


@pytest.mark.API
@pytest.mark.FUNC
def test_putting_objects_with_versionning_enabled(minio_mock):
    client = Minio("http://local.host:9000")
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_path = "tests/fixtures/maya.jpeg"
    client.make_bucket(bucket_name)
    # Versioning Enabled
    client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
    # Add two objects
    client.fput_object(bucket_name, object_name, file_path)
    client.fput_object(bucket_name, object_name, file_path)
    # they should be two versions of the same object
    # check list_objects with include_version=False returns only one object with is_latest=True
    objects = list(client.list_objects(bucket_name, object_name, include_version=False))
    assert len(objects) == 1
    # check that versions are stored correctly and retrieved correctly
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 2
    with pytest.raises(S3Error, match="Invalid version"):
        client.get_object(bucket_name, object_name, version_id="wrong")


@pytest.mark.API
@pytest.mark.FUNC
def test_removing_object_version_with_versionning_enabled(minio_mock):
    client = Minio("http://local.host:9000")
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_path = "tests/fixtures/maya.jpeg"
    client.make_bucket(bucket_name)

    # Versioning Enabled
    client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
    # Add two objects
    client.fput_object(bucket_name, object_name, file_path)
    client.fput_object(bucket_name, object_name, file_path)

    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    first_version = objects[0].version_id
    last_version = objects[1].version_id

    client.remove_object(bucket_name, object_name, version_id=first_version)
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 1
    assert objects[0].version_id == last_version
    assert objects[0].is_latest == "true"

    client.fput_object(bucket_name, object_name, file_path)
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 2
    first_version = objects[0].version_id
    assert first_version != last_version


@pytest.mark.API
@pytest.mark.FUNC
def test_putting_and_removing_and_listing_bjecst_with_versionning_enabled(minio_mock):
    client = Minio("http://local.host:9000")
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_path = "tests/fixtures/maya.jpeg"
    client.make_bucket(bucket_name)

    # Versioning Enabled
    client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
    # Add two objects
    client.fput_object(bucket_name, object_name, file_path)
    client.fput_object(bucket_name, object_name, file_path)
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 2
    # removing the object with versioning enabled will add a delete marker
    client.remove_object(bucket_name, object_name)
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 3
    assert objects[-1].is_delete_marker == True

    # removing the object again will have no effect
    client.remove_object(bucket_name, object_name)
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 3

    # listing an object marked for deletion will return an empty list
    objects = list(client.list_objects(bucket_name, object_name))
    assert len(objects) == 0

    # putting a new version after deletion will add a new version
    client.fput_object(bucket_name, object_name, file_path)
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 4

    objects = list(client.list_objects(bucket_name, object_name))
    assert len(objects) == 1

    # removing the object again with versioning enabled will add a new deletion marker
    client.remove_object(bucket_name, object_name)
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 5

    # trying to an object marked for deletion by version will raise an exception
    with pytest.raises(S3Error) as error:
        client.get_object(bucket_name, object_name, version_id=objects[3].version_id)
    assert "not allowed against this resource" in str(error.value)

    # trying to an object marked for deletion by version will raise an exception
    with pytest.raises(S3Error) as error:
        client.get_object(bucket_name, object_name, version_id=objects[4].version_id)
    assert "not allowed against this resource" in str(error.value)

    objects = list(client.list_objects(bucket_name, object_name))
    assert len(objects) == 0


@pytest.mark.API
@pytest.mark.FUNC
def test_versioned_objects_after_upload(minio_mock):
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_path = "tests/fixtures/maya.jpeg"

    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    client.fput_object(bucket_name, object_name, file_path)
    client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 1
    first_version = objects[0].version_id
    assert first_version == "null"

    client.fput_object(bucket_name, object_name, file_path)
    client.fput_object(bucket_name, object_name, file_path)
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    last_version = objects[1].version_id
    assert len(objects) == 3
    assert objects[-1].version_id == "null"
    assert last_version is not None
    client.set_bucket_versioning(bucket_name, VersioningConfig(SUSPENDED))

    objects = list(client.list_objects(bucket_name, object_name, include_version=True))

    client.remove_object(bucket_name, object_name, objects[0].version_id)
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 2

    client.remove_object(bucket_name, object_name)
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 2
    assert objects[-1].is_delete_marker == True

    client.remove_object(bucket_name, object_name, "null")
    objects = list(client.list_objects(bucket_name, object_name, include_version=True))
    assert len(objects) == 1


@pytest.mark.UNIT
@pytest.mark.API
@pytest.mark.FUNC
@pytest.mark.parametrize("versioned", (True, False))
def test_file_download(minio_mock, versioned):
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_content = b"Test file content"
    length = sys.getsizeof(file_content)
    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    version = None
    if versioned:
        client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
    client.put_object(bucket_name, object_name, file_content, length)
    if versioned:
        version = list(
            client.list_objects(bucket_name, object_name, include_version=True)
        )[0].version_id

    response = client.get_object(bucket_name, object_name)
    downloaded_content = response.data

    assert (
        downloaded_content == file_content
    ), "Downloaded content should match the original"
    if versioned:
        response = client.get_object(bucket_name, object_name, version_id=version)
        downloaded_content = response.data

        assert (
            downloaded_content == file_content
        ), "Downloaded content should match the original"


@pytest.mark.UNIT
@pytest.mark.API
def test_bucket_exists(minio_mock):
    bucket_name = "existing-bucket"
    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    assert client.bucket_exists(bucket_name), "Bucket should exist"


@pytest.mark.UNIT
@pytest.mark.API
def test_bucket_versioning(minio_mock):
    bucket_name = "existing-bucket"
    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    assert client.get_bucket_versioning(bucket_name).status == "Off"
    client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
    assert client.get_bucket_versioning(bucket_name).status == "Enabled"
    client.set_bucket_versioning(bucket_name, VersioningConfig("Suspended"))
    assert client.get_bucket_versioning(bucket_name).status == "Suspended"


@pytest.mark.UNIT
@pytest.mark.API
@pytest.mark.parametrize("versioned", (True, False))
def test_get_presigned_url(minio_mock, versioned):
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_path = "tests/fixtures/maya.jpeg"

    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    version = None
    if versioned:
        client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
    client.fput_object(bucket_name, object_name, file_path)
    if versioned:
        version = list(
            client.list_objects(bucket_name, object_name, include_version=True)
        )[-1].version_id
    url = client.get_presigned_url("GET", bucket_name, object_name, version_id=version)
    assert validators.url(url)
    if version:
        assert url.endswith(f"?versionId={version}")


@pytest.mark.UNIT
@pytest.mark.API
def test_presigned_put_url(minio_mock):
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_path = "tests/fixtures/maya.jpeg"

    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    client.fput_object(bucket_name, object_name, file_path)
    url = client.presigned_put_object(bucket_name, object_name)
    assert validators.url(url)


@pytest.mark.UNIT
@pytest.mark.API
def test_presigned_get_url(minio_mock):
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_path = "tests/fixtures/maya.jpeg"

    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    client.fput_object(bucket_name, object_name, file_path)
    url = client.presigned_get_object(bucket_name, object_name)
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
    assert len(buckets) == n + 1
    assert "new-bucket" in {b.name for b in buckets}
    assert all(isinstance(b, Bucket) for b in buckets)


@pytest.mark.REGRESSION
@pytest.mark.UNIT
@pytest.mark.API
def test_list_objects(minio_mock):
    client = Minio("http://local.host:9000")

    with pytest.raises(S3Error):
        _ = client.list_objects("no-such-bucket")

    bucket_name = "new-bucket"
    client.make_bucket(bucket_name)
    objects = client.list_objects(bucket_name)
    assert len(list(objects)) == 0

    client.put_object(bucket_name, "a/b/c/object1", data=b"object1 data", length=12)
    client.put_object(bucket_name, "a/b/object2", data=b"object2 data", length=12)
    client.put_object(bucket_name, "a/object3", data=b"object3 data", length=11)
    client.put_object(bucket_name, "object4", data=b"object4 data", length=11)

    # Test recursive listing
    objects_recursive = list(
        client.list_objects(bucket_name, prefix="a/", recursive=True)
    )
    assert len(objects_recursive) == 3, "Expected 3 objects under 'a/' with recursion"
    # Check that all expected paths are returned
    assert set(obj.object_name for obj in objects_recursive) == {
        "a/b/c/object1",
        "a/b/object2",
        "a/object3",
    }

    # Test non-recursive listing
    objects_non_recursive = client.list_objects(
        bucket_name, prefix="a/", recursive=False
    )

    # Check that the correct path is returned
    assert set(obj.object_name for obj in objects_non_recursive) == {
        "a/object3",
        "a/b/",
    }

    # Test listing at the bucket root
    objects_root = client.list_objects(bucket_name, recursive=False)
    # Check that the correct paths are returned
    assert set(obj.object_name for obj in objects_root) == {"a/", "object4"}


@pytest.mark.REGRESSION
def test_connecting_to_the_same_endpoint(minio_mock):
    client_1 = Minio("http://local.host:9000")
    client_1_buckets = ["bucket-1", "bucket-2", "bucket-3"]
    for bucket in client_1_buckets:
        client_1.make_bucket(bucket)

    client_2 = Minio("http://local.host:9000")
    client_2_buckets = client_2.list_buckets()
    assert client_2_buckets == client_1_buckets


@pytest.mark.UNIT
def test_stat_object(minio_mock):
    bucket_name = "test-bucket"
    object_name = "test-object"
    file_path = "tests/fixtures/maya.jpeg"

    client = Minio("http://local.host:9000")
    client.make_bucket(bucket_name)
    client.fput_object(bucket_name, object_name, file_path)

    object_stat = client.stat_object(bucket_name=bucket_name, object_name=object_name)

    assert object_stat.bucket_name == bucket_name
    assert object_stat.object_name == object_name
    assert object_stat.version_id is None

    client.remove_object(bucket_name, object_name)

    with pytest.raises(S3Error) as error:
        _ = client.stat_object(bucket_name=bucket_name, object_name=object_name)
    assert error.value.code == "NoSuchKey"
    assert error.value.message == "Object does not exist"

    client.fput_object(bucket_name, object_name, file_path)
    client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))

    object_stat = client.stat_object(bucket_name=bucket_name, object_name=object_name)
    assert object_stat.bucket_name == bucket_name
    assert object_stat.object_name == object_name
    assert object_stat.version_id is None
    object_stat = client.stat_object(
        bucket_name=bucket_name, object_name=object_name, version_id="null"
    )
    assert object_stat.bucket_name == bucket_name
    assert object_stat.object_name == object_name
    assert object_stat.version_id is None
    client.fput_object(bucket_name, object_name, file_path)
    objects = list(client.list_objects(bucket_name=bucket_name, include_version=True))
    object_stat = client.stat_object(
        bucket_name=bucket_name,
        object_name=object_name,
        version_id=objects[1].version_id,
    )
    assert object_stat.version_id is None


@pytest.mark.REGRESSION
@pytest.mark.UNIT
def test_fget_object(minio_mock, tmp_path):
    client = Minio("http://local.host:9000")

    bucket_name = "new-bucket"
    client.make_bucket(bucket_name)
    objects = client.list_objects(bucket_name)
    assert len(list(objects)) == 0

    client.put_object(bucket_name, "object1", data=b"object1 data", length=12)

    file_path = tmp_path  # should raise a Value error
    with pytest.raises(ValueError):
        _ = client.fget_object(bucket_name, "object1", file_path)

    file_path = os.path.join(tmp_path, "object1.dat")
    stat = client.fget_object(bucket_name, "object1", file_path)
    assert isinstance(stat, Object)

    # folder objects does not exist, fget_object should create it
    file_path = os.path.join(tmp_path, "another_folder", "object1.dat")
    stat = client.fget_object(bucket_name, "object1", file_path)
    assert isinstance(stat, Object)

    # folder objects does not exist, fget_object should create it
    file_path = os.path.join(tmp_path, "another_folder", "object1.dat")
    stat = client.fget_object(bucket_name, "object1", file_path)
    assert isinstance(stat, Object)
