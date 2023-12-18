import datetime
import io
import logging

import pytest
import validators
from minio import Minio
from minio.datatypes import Bucket
from minio.error import S3Error
from urllib3.connection import HTTPConnection
from urllib3.response import HTTPResponse


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

    def _health_check(self):
        if not self._base_url:
            raise Exception("base_url is empty")
        if not validators.hostname(self._base_url) and not validators.url(
            self._base_url
        ):
            raise Exception(f"base_url {self._base_url} is not valid")

    def fput_object(self, bucket_name, object_name, file_path, *args, **kwargs):
        # Mock behavior for fput_object
        # if bucken_name does not exists raise some error
        self._health_check()
        if not self.bucket_exists(bucket_name):
            # TODO: Check the actual behavior of fput_object
            raise S3Error("bucket does not exist")
        self.buckets[bucket_name][object_name] = file_path
        return "Upload successful"

    def put_object(self, bucket_name, object_name, data, *args, **kwargs):
        self._health_check()
        if not self.bucket_exists(bucket_name):
            raise S3Error("bucket does not exist")
        self.buckets[bucket_name][object_name] = data
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
            raise S3Error("no suck bucket")

        bucket = self.buckets[bucket_name]
        for obj_name in bucket:
            if obj_name.startswith(prefix) and (
                start_after == "" or obj_name > start_after
            ):
                # Here, just returning object name for simplicity
                yield obj_name

    def get_object(self, bucket_name, object_name):
        self._health_check()
        # do something to self.buckets[bucket_name] = {}
        data = self.buckets[bucket_name][object_name]
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
def minio_mock(mocker):
    def minio_mock_init(
        cls,
        *args,
        **kwargs,
    ):
        return MockMinioClient(*args, **kwargs)

    patched = mocker.patch.object(Minio, "__new__", new=minio_mock_init)
    yield patched
