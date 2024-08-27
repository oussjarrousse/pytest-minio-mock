"""
"""
import pytest
from minio.commonconfig import ENABLED
from minio.versioningconfig import OFF
from minio.versioningconfig import VersioningConfig

from pytest_minio_mock.plugin import MockMinioBucket


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
