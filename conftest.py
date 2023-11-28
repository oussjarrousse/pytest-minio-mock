import pytest
from pytest_minio_mock.minio_mock import MockMinioClient
from minio import Minio

@pytest.fixture
def minio_mock(mocker):
    def minio_mock_init(
        cls,
        *args,
        **kwargs,
    ):
        return MockMinioClient(
            *args,
            **kwargs
        )

    p = mocker.patch.object(Minio, "__new__", new=minio_mock_init)
    yield