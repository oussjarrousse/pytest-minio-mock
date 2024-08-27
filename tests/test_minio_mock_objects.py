"""
"""
import pytest

from pytest_minio_mock.plugin import MockMinioObject


@pytest.mark.UNIT
class TestsMockMinioObject:
    @pytest.mark.UNIT
    def test_mock_minio_object_init(self):
        mock_minio_object = MockMinioObject("test-bucket", "test-object")
        assert mock_minio_object.versions == {}
