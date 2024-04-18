import pytest
from pytest_minio_mock.plugin import minio_mock
from pytest_minio_mock.plugin import minio_mock_servers
from minio import Minio


@pytest.fixture(autouse=True)
def _clean(minio_mock):
    client = Minio("http://local.host:9000")
    client.buckets = {}
