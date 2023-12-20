import datetime
import io
import logging
import os

import pytest
import validators
from minio import Minio
from minio.datatypes import Bucket
from minio.error import S3Error
from urllib3.connection import HTTPConnection
from urllib3.response import HTTPResponse


class Object:
    def __init__(self, object_name, data):
        self._object_name = object_name
        self._data = data

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def object_name(self):
        return self._object_name


class Server:
    def __init__(self, endpoint):
        self._base_url = endpoint
        self._buckets = {}

    @property
    def base_url(self):
        return self._base_url

    @property
    def bucket(self):
        return self._buckets

    def __getitem__(self, item):
        return self._buckets[item]

    def __setitem__(self, key, value):
        self._buckets[key] = value

    def __len__(self):
        return len(self._buckets)

    def keys(self):
        return self._buckets.keys()

    def values(self):
        return self._buckets.values()

    def items(self):
        return self._buckets.items()

    def get(self, key, default=None):
        return self._buckets.get(key, default)

    def pop(self, key, default=None):
        return self._buckets.pop(key, default) if key in self._buckets else default

    def update(self, other):
        self._buckets.update(other)

    def __contains__(self, item):
        return item in self._buckets

    def __delitem__(self, key):
        del self._buckets[key]

    def __iter__(self):
        return iter(self._buckets)


class Servers:
    def __init__(self):
        self.servers = {}

    def connect(self, endpoint):
        if endpoint not in self.servers:
            self.servers[endpoint] = Server(endpoint)
        return self.servers[endpoint]

    def reset(self):
        self.servers = {}


class MockMinioClient:
    def __init__(
        self,
        endpoint,
        access_key=None,
        secret_key=None,
        session_token=None,
        secure=True,
        region=None,
        http_client=None,
        credentials=None,
    ):
        self._base_url = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._session_token = session_token
        self._secure = secure
        self._region = region
        self._http_client = http_client
        self._credentials = credentials
        self.buckets = {}

    def _connect(self, servers):
        self.buckets = servers.connect(self._base_url)

    def _health_check(self):
        if not self._base_url:
            raise Exception("base_url is empty")
        if not validators.hostname(self._base_url) and not validators.url(
            self._base_url
        ):
            raise Exception(f"base_url {self._base_url} is not valid")

    def fget_object(
        self,
        bucket_name,
        object_name,
        file_path,
        request_headers=None,
        sse=None,
        version_id=None,
        extra_query_params=None,
    ):
        object = self.get_object(bucket_name, object_name)
        with open(file_part_path, "wb") as f:
            f.write(object.data)

    def get_object(
        self,
        bucket_name,
        object_name,
        offset: int = 0,
        length: int = 0,
        request_headers=None,
        ssec=None,
        version_id=None,
        extra_query_params=None,
    ):
        self._health_check()
        # do something to self.buckets[bucket_name] = {}
        the_object = self.buckets[bucket_name][object_name]
        data = the_object.data
        # Create a buffer containing the data
        if isinstance(data, io.BytesIO):
            body = copy.deepcopy(data)
        if isinstance(data, bytes):
            body = data
        else:
            body = io.BytesIO(data.encode("utf-8"))

        conn = HTTPConnection("localhost")
        response = HTTPResponse(body=body, preload_content=False, connection=conn)
        return response

    def fput_object(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
        metadata=None,
        sse=None,
        progress=None,
        part_size: int = 0,
        # num_parallel_uploads: int = 3,
        # tags = None,
        # retention = None,
        # legal_hold: bool = False,
    ):
        # Mock behavior for fput_object
        # if bucken_name does not exists raise some error
        self._health_check()
        if not self.bucket_exists(bucket_name):
            # TODO: Check the actual behavior of fput_object
            raise S3Error(
                message="bucket does not exist",
                resource=bucket_name,
                request_id=None,
                host_id=None,
                response="mocked_response",
                code=404,
                bucket_name=bucket_name,
                object_name=None,
            )
        file_size = os.stat(file_path).st_size
        with open(file_path, "rb") as file_data:
            return self.put_object(
                bucket_name,
                object_name,
                file_data,
                length=file_size,
                content_type="application/octet-stream",
                metadata=metadata,
                sse=sse,
                progress=progress,
                part_size=part_size,
            )

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data,
        length: int,
        content_type: str = "application/octet-stream",
        metadata=None,
        sse=None,
        progress=None,
        part_size: int = 0
        # num_parallel_uploads: int = 3,
        # tags = None,
        # retention = None,
        # legal_hold: bool = False
    ):
        self._health_check()
        if not self.bucket_exists(bucket_name):
            raise S3Error(
                message="bucket does not exist",
                resource=bucket_name,
                request_id=None,
                host_id=None,
                response="mocked_response",
                code=404,
                bucket_name=bucket_name,
                object_name=None,
            )
        self.buckets[bucket_name][object_name] = Object(
            object_name=object_name, data=data
        )
        return "Upload successful"

    def get_presigned_url(
        self,
        method,
        bucket_name,
        object_name,
        expires=datetime.timedelta(days=7),
        response_headers=None,
        request_date=None,
        version_id=None,
        extra_query_params=None,
    ):
        return "{}/{}/{}".format(self._base_url, bucket_name, object_name)

    def list_buckets(self):
        try:
            self._health_check()
            buckets_list = []
            for bucket_name in self.buckets.keys():
                buckets_list.append(bucket_name)
            return buckets_list
        except Exception as e:
            raise e

    def bucket_exists(self, bucket_name):
        self._health_check()
        try:
            self.buckets[bucket_name]
        except KeyError:
            return False
        except Exception as e:
            raise
        return True

    def make_bucket(self, bucket_name, location=None, object_lock=False):
        self._health_check()
        self.buckets[bucket_name] = {
            #  "__META__":
            # {"name":bucket_name,
            # "creation_date":datetime.datetime.utcnow()}
        }
        return True

    def list_objects(self, bucket_name, prefix="", recursive=False, start_after=""):
        # Mock implementation
        if bucket_name not in self.buckets:
            raise S3Error(
                message="bucket does not exist",
                resource=bucket_name,
                request_id=None,
                host_id=None,
                response="mocked_response",
                code=404,
                bucket_name=bucket_name,
                object_name=None,
            )
        bucket = self.buckets[bucket_name]
        bucket_objects = []
        for obj_name in bucket:
            if obj_name.startswith(prefix) and (
                start_after == "" or obj_name > start_after
            ):
                # Here, just returning object name for simplicity
                bucket_objects.append(obj_name)
        return bucket_objects

    def remove_object(self, bucket_name, object_name):
        self._health_check()
        try:
            del self.buckets[bucket_name][object_name]
            return
        except Exception:
            logging.error("remove_object(): Exception")
            logging.error(self.buckets)
            raise


@pytest.fixture
def minio_mock_servers():
    yield Servers()


@pytest.fixture
def minio_mock(mocker, minio_mock_servers):
    def minio_mock_init(
        cls,
        *args,
        **kwargs,
    ):
        client = MockMinioClient(*args, **kwargs)
        client._connect(minio_mock_servers)
        return client

    patched = mocker.patch.object(Minio, "__new__", new=minio_mock_init)
    yield patched
