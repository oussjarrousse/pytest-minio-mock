"""
A pytest plugin for mocking Minio S3 interactions. This module provides a mock Minio client and
server setup to facilitate testing of applications that interact with Minio S3 storage without the
need for a real Minio server. It's designed to mimic the behavior of the real Minio client to a
degree that is useful for testing purposes.

Classes:
    MockMinioObjectVersion: Represents a mock object version stored in Minio.
    MockMinioObject: Represents a mock object stored in Minio.
    MockMinioBucket: Represents a mock bucket stored in Minio.
    MockMinioServer: Represents a single mock Minio server.
    MockMinioServers: Manages multiple mock Minio server instances.
    MockMinioClient: A mock version of the Minio client.

Fixtures:
    minio_mock_servers: A pytest fixture providing a Servers instance.
    minio_mock: A pytest fixture to patch the Minio client with a mock for testing.

This module allows you to test file uploads, downloads, bucket creations, and other Minio operations
by simulating the Minio environment. It's useful in scenarios where you want to ensure your
application interacts correctly with Minio, without the overhead of connecting to an actual Minio
server.
"""
import copy
import datetime
import errno
import io
import logging
import os
from uuid import uuid4

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
from urllib3.connection import HTTPConnection
from urllib3.response import HTTPResponse


# Define a simple class or named tuple to hold object info
# ObjectInfo = namedtuple("ObjectInfo", ["object_name"])


class MockMinioObjectVersion:
    """
    Represents a mock object version in Minio storage.

    Attributes:
        object_name (str): The name of the object.
        data (bytes or io.BytesIO): The data the object contains.
        version_id (str, optional): The version of the object.
        is_delete_marker (bool): whether this object is marked as deleted on a
          versioned bucket
    """

    def __init__(self, object_name, data, version_id, is_delete_marker, is_latest):
        """
        Initialize the MockMinioObjectVersion with a name and data.

        Args:
            object_name (str): The name of the object.
            data (bytes or io.BytesIO): The data the object contains.
            version_id (str, optional): The version of the object.
            is_delete_marker (bool): whether this object is marked as deleted on a
              versioned bucket
        """
        self._object_name = object_name
        self._data = data
        self._version_id = version_id
        self._is_delete_marker = is_delete_marker
        self._last_modified = datetime.datetime.utcnow()
        self._is_latest = is_latest

    @property
    def data(self):
        """Get the data the object contains."""
        return self._data

    @property
    def version_id(self):
        """Get the version of the object."""
        return self._version_id

    @property
    def last_modified(self):
        """return the last modified datetime of the object."""
        return self._last_modified

    @property
    def is_delete_marker(self):
        """Is the object deleted n a versioned bucket ?"""
        return self._is_delete_marker

    @is_delete_marker.setter
    def is_delete_marker(self, value):
        self._is_delete_marker = value

    @data.setter
    def data(self, value):
        """Set the data the object contains."""
        self._data = value

    @property
    def object_name(self):
        """Get the name of the object."""
        return self._object_name

    @property
    def is_latest(self):
        """is this object marked latest"""
        return self._is_latest

    @is_latest.setter
    def is_latest(self, value):
        """Set the value of is_latest"""
        self._is_latest = value


class MockMinioObject:
    """
    Represents a mock object in Minio storage.
    """

    def __init__(self, bucket_name, object_name):
        self._bucket_name = bucket_name
        self._object_name = object_name
        self._versions = {}

    @property
    def bucket_name(self):
        """Get the name of the bucket"""
        return self._bucket_name

    @property
    def object_name(self):
        """Get the name of the object stored at initialization"""
        return self._object_name

    @property
    def versions(self):
        """Get the versions stored in the object"""
        return self._versions

    def reset_latest(self):
        """
        Sets the value of the latest flag to False in all object versions
        """
        for _, obj in self._versions.items():
            if obj.is_latest:
                obj.is_latest = False
        return

    def get_latest(self):
        """
        Returns:
            The version that is marked latest.
            If the object has no versions, it returns None.
            if none of the versions is marked latest it raises an exception that indicates an implementation error
        """
        if not self._versions:
            return None
        for _, obj in self._versions.items():
            if obj.is_latest:
                return obj
        raise RuntimeError("Implemnetation Error")

    def put_object_version(self, version_id, obj: MockMinioObjectVersion):
        """
        Inserts an object version in the _versions map.
        """
        self.reset_latest()
        obj.is_latest = True
        self._versions[version_id] = obj

    def put_object(
        self,
        object_name: str,
        data,
        length: int,
        content_type: str = "application/octet-stream",
        metadata=None,
        sse=None,
        progress=None,
        part_size: int = 0,
        # num_parallel_uploads: int = 3,
        # tags = None,
        # retention = None,
        # legal_hold: bool = False,
        versioning: VersioningConfig = VersioningConfig(),
    ):
        """
        Returns:
            the put object
        """

        # According to
        # https://min.io/docs/minio/linux/administration/object-management/object-versioning.html#suspend-bucket-versioning
        # objects created when versioning is suspended have a 'null' version ID (None in Python)

        version_id = "null"
        # If status is enabled, create a new version UUID
        if versioning.status == ENABLED:
            version_id = str(uuid4())

        obj = MockMinioObjectVersion(
            object_name=object_name,
            data=data,
            version_id=version_id,
            is_delete_marker=False,
            is_latest=True,
        )
        # If versioning is OFF, there can only be one version of an object (store a read version_id non-the-less)
        if versioning.status == OFF:
            self._versions = {}

        self.put_object_version(version_id, obj)
        return obj

    def stat_object(
        self,
        version_id,
        versioning: VersioningConfig,
        ssec=None,
        extra_headers=None,
        extra_query_params=None,
    ):
        """
        Returns
            the stat of the object if versioning is disabled
            the stat of the latest version of the object if versioning is enabled
        """
        obj_version = self.get_object(version_id=version_id, versioning=versioning)
        the_stat_object_version = Object(
            bucket_name=self.bucket_name,
            object_name=self.object_name,
            last_modified=obj_version.last_modified,
            version_id=None
            if obj_version.version_id == "null"
            else obj_version.version_id,
            is_latest="true" if obj_version.is_latest else "false",
            is_delete_marker=obj_version.is_delete_marker,
        )

        return the_stat_object_version

    def get_object(self, version_id, versioning: VersioningConfig):
        """
        Returns
            the stored object if versioning is disabled
            the latest version of the object if versioning is enabled
        """
        if version_id and version_id != "null" and not validators.uuid(version_id):
            raise S3Error(
                message="Invalid version id specified",
                resource=f"/{self.bucket_name}/{self.object_name}",
                request_id=None,
                host_id=None,
                response="mocked_response",
                code=422,
                bucket_name=self.bucket_name,
                object_name=self.object_name,
            )

        # If version == None, give version_id a value
        if not version_id:
            if not self._versions:
                raise S3Error(
                    # code=NoSuchKey
                    message="The specified key does not exist.",
                    resource="",
                    request_id=None,
                    host_id=None,
                    response="mocked_response",
                    code=404,
                    bucket_name=None,
                    object_name=self.object_name,
                )

            # if versioning is disabled, look for the object with version_id = "null"
            if versioning.status == OFF:
                version_id = "null"
            # if versioning is enabled or suspended, get the version_id of the latest_version
            else:
                latest_object_version = self.get_latest()
                if latest_object_version:
                    version_id = latest_object_version.version_id

        # now try to get the object with that version_id
        try:
            the_object_version = self._versions[version_id]
        except KeyError as exc:
            raise S3Error(
                message="The specified version does not exist",
                resource="",
                request_id=None,
                host_id=None,
                response="mocked_response",
                code=404,
                bucket_name=None,
                object_name=self.object_name,
            ) from exc

        # if the delete_marker is set raise an error
        if the_object_version.is_delete_marker:
            raise S3Error(
                message="The specified method is not allowed against this resource.",
                resource="",
                request_id=None,
                host_id=None,
                response="mocked_response",
                code=403,
                bucket_name=None,
                object_name=self.object_name,
            )
        return the_object_version

    def list_versions(self):
        versions_list = list(
            sorted(
                self._versions.items(),
                key=lambda i: (
                    i[1].is_delete_marker,
                    -i[1].last_modified.timestamp(),
                ),
            )
        )
        return versions_list

    def remove_object(self, version_id, versioning: VersioningConfig):
        """
        Returns
            nothing
        """
        try:
            if versioning.status == OFF:
                if version_id:
                    if version_id in self.versions:
                        del self.versions[version_id]
                else:
                    raise RuntimeError("This should not happen")
                return
        except Exception as e:
            logging.error("remove_object(): Exception")
            logging.error(e)
            raise e
        try:
            if versioning.status == ENABLED:
                if version_id:
                    if version_id not in self.versions:
                        # version_id does not exist,
                        # nothing to do
                        return
                    else:
                        latest_obj = self.get_latest()
                        del self.versions[version_id]
                        if version_id == latest_obj.version_id:
                            obj = list(self.versions.values())[0]
                            obj.is_latest = True
                else:  # version_id is False
                    latest_obj = self.get_latest()
                    if latest_obj.is_delete_marker:
                        # nothing to do
                        return

                    version_id = str(uuid4())

                    obj = MockMinioObjectVersion(
                        object_name=self.object_name,
                        data=b"",
                        version_id=version_id,
                        is_delete_marker=True,
                        is_latest=True,
                    )
                    self.put_object_version(version_id=obj.version_id, obj=obj)
                    return
            elif versioning.status == SUSPENDED:
                if version_id:
                    latest_obj = self.get_latest()
                    del self.versions[version_id]
                    if version_id == latest_obj.version_id:
                        obj = list(self.versions.values())[0]
                        obj.is_latest = True
                else:
                    latest_obj = self.get_latest()
                    latest_obj.is_delete_marker = True
            else:
                raise Exception("unexpected")
        except Exception as e:
            logging.error("remove_object(): Exception")
            logging.error(e)
            raise


class MockMinioBucket:
    """
    Represents a mock Bucket in Minio storage.
    """

    def __init__(
        self,
        bucket_name,
        versioning: VersioningConfig,
        location=None,
        object_lock=False,
    ):
        self._bucket_name = bucket_name
        self._versioning = versioning
        self._objects = {}
        self._location = location
        self._object_lock = object_lock
        self._creation_date = datetime.datetime.now()

    @property
    def bucket_name(self):
        """Gets the name of the bucket stored at initialization."""
        return self._bucket_name

    @property
    def objects(self):
        """Get the objects stored in the bucket."""
        return self._objects

    @property
    def versioning(self):
        """Get the the config of versioning of the bucket."""
        return self._versioning

    @versioning.setter
    def versioning(self, versioning: VersioningConfig):
        """Set the versioning config of the bucket."""
        self._versioning = versioning

    def put_object(
        self,
        object_name: str,
        data,
        length: int,
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
        """
        Returns
            newly added object
        """
        if object_name not in self.objects:
            self.objects[object_name] = MockMinioObject(self.bucket_name, object_name)

        obj = self.objects[object_name].put_object(
            object_name=object_name,
            data=data,
            length=length,
            content_type=content_type,
            metadata=metadata,
            sse=sse,
            progress=progress,
            part_size=part_size,
            # num_parallel_uploads: int = 3,
            # tags = None,
            # retention = None,
            # legal_hold: bool = False,
            versioning=self.versioning,
        )

        return obj

    def remove_object(self, object_name, version_id=None):
        """ """
        if object_name not in self.objects:
            # Object does not exist, so nothing to do
            return
        try:
            if self.versioning.status == OFF:
                if not version_id:
                    del self.objects[object_name]
                    return
            return self.objects[object_name].remove_object(version_id, self.versioning)

        except Exception as e:
            logging.error("remove_object(): Exception")
            logging.error(e)
            raise

    def get_object(self, object_name, version_id):
        try:
            the_object = self.objects[object_name]
        except KeyError as exc:
            raise S3Error(
                message="The specified key does not exist.",
                resource=f"/{self.bucket_name}/{object_name}",
                request_id=None,
                host_id=None,
                response="mocked_response",
                code=404,
                bucket_name=self.bucket_name,
                object_name=object_name,
            ) from exc

        try:
            the_object_version = the_object.get_object(version_id, self.versioning)
        except S3Error as e:
            raise S3Error(
                message=e.message,
                response=e.response,
                resource=f"/{self.bucket_name}/{object_name}",
                host_id=None,
                request_id=None,
                code=e.code,
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
        return the_object_version

    def stat_object(
        self,
        object_name,
        ssec=None,
        version_id=None,
        extra_headers=None,
        extra_query_params=None,
    ) -> Object:
        """
        Get object information and metadata of an object in the mock Minio server

        Args:
            object_name (str): The name of the object to remove.
            ssec (SseCustomerKey| None, optional): Server-side encryption customer key.
            version_id (str | None, optional): The version about which to retrieve information and metadata.
            extra_headers ( dict | None, optional ):
            extra_query_params ( dict | None, optional): Extra query parameters for advanced usage.

        Returns:
            Object: Object information as Object.
        """

        try:
            the_object = self.objects[object_name]
        except KeyError as e:
            raise S3Error(
                message="Object does not exist",
                resource=f"/{self.bucket_name}/{object_name}",
                request_id=None,
                host_id=None,
                response="mocked_response",
                code="NoSuchKey",
                bucket_name=self.bucket_name,
                object_name=object_name,
            )

        try:
            the_object_version_stat = the_object.stat_object(
                version_id=version_id,
                versioning=self.versioning,
                ssec=ssec,
                extra_headers=extra_headers,
                extra_query_params=extra_query_params,
            )
        except S3Error as e:
            raise S3Error(
                message=e.message,
                response=e.response,
                resource=f"/{self.bucket_name}/{object_name}",
                host_id=None,
                request_id=None,
                code=e.code,
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
        return the_object_version_stat

    def list_objects(
        self,
        prefix=None,
        recursive=False,
        start_after=None,
        include_version=False,
    ):
        """
        Returns
            Iterator of MockMinioObjectVersions of the current bucket
        """
        # Initialization
        # bucket_objects = []
        seen_prefixes = set()
        if prefix is None:
            prefix = ""

        # Note: Wrapped items() in list(.) to allow modification during iteration
        for object_name, obj in list(self.objects.items()):
            if object_name.startswith(prefix) and (
                not start_after or object_name > start_after
            ):
                # Handle non-recursive listing by identifying and adding unique directory names
                if not recursive:
                    sub_path = object_name[len(prefix) :].strip("/")
                    dir_end_idx = sub_path.find("/")
                    if dir_end_idx != -1:
                        dir_name = prefix + sub_path[: dir_end_idx + 1]
                        if dir_name not in seen_prefixes:
                            seen_prefixes.add(dir_name)
                            yield Object(
                                bucket_name=self.bucket_name, object_name=dir_name
                            )
                        # Skip further processing to prevent
                        # adding the full object path
                        continue
                # Directly add the object for recursive listing
                # or if it's a file in the current directory
                if include_version:
                    # Minio API always sort versions by time,
                    # it also includes delete markers at the end newwst first
                    versions_list = obj.list_versions()
                    for version_id, obj_version in versions_list:
                        yield Object(
                            bucket_name=self.bucket_name,
                            object_name=object_name,
                            last_modified=obj_version.last_modified,
                            version_id=version_id,
                            is_latest="true" if obj_version.is_latest else "false",
                            is_delete_marker=obj_version.is_delete_marker,
                        )
                else:
                    obj_version = obj.get_latest()
                    # only yield if the object is not a delete marker
                    if not obj_version.is_delete_marker:
                        yield Object(
                            bucket_name=self.bucket_name,
                            object_name=object_name,
                            last_modified=obj_version.last_modified,
                            version_id=None,
                            is_latest=None,
                            is_delete_marker=obj_version.is_delete_marker,
                        )


class MockMinioServer:
    """
    Represents a mock Minio server.

    Attributes:
        _base_url (str): The endpoint URL of the server.
        _buckets (dict): A dictionary to hold bucket data.
    """

    def __init__(self, endpoint):
        """
        Initialize the MockMinioServer with the given endpoint.

        Args:
            endpoint (str): The endpoint URL for the mock server.
        """
        self._base_url = endpoint
        self._buckets = {}

    @property
    def base_url(self):
        """Get the base URL of the server."""
        return self._base_url

    @property
    def buckets(self):
        """Get the dictionary of buckets in the server."""
        return self._buckets

    def __getitem__(self, item):
        return self._buckets[item]

    def __setitem__(self, key, value):
        self._buckets[key] = value

    def __len__(self):
        return len(self._buckets)

    def keys(self):
        """Returns the keys of the self._buckets dictionary."""
        return self._buckets.keys()

    def values(self):
        """Returns the values of the self._buckets dictionary."""
        return self._buckets.values()

    def items(self):
        """Returns the items of the self._buckets dictionary."""
        return self._buckets.items()

    def get(self, key, default=None):
        """get a specific bucket,
        or default if key is not in the self._buckets dictionary.
        """
        return self._buckets.get(key, default)

    def pop(self, key, default=None):
        """pops a specific bucket."""
        return self._buckets.pop(key, default) if key in self._buckets else default

    def update(self, other):
        """updates the self._buckets dictionary with another dictionary."""
        self._buckets.update(other)

    def __contains__(self, item):
        return item in self._buckets

    def __delitem__(self, key):
        del self._buckets[key]

    def __iter__(self):
        return iter(self._buckets)


class MockMinioServers:
    """
    Manages multiple MockMinioServer instances.

    Attributes:
        servers (dict): A dictionary to hold Server instances.
    """

    def __init__(self):
        """Initialize the Servers with an empty dictionary."""
        self.servers = {}

    def connect(self, endpoint):
        """
        Connect to a mock server with the given endpoint. Create a new one if it doesn't exist.

        Args:
            endpoint (str): The endpoint URL of the server to connect to.

        Returns:
            Server: The connected mock server.
        """
        if endpoint not in self.servers:
            self.servers[endpoint] = MockMinioServer(endpoint)
        return self.servers[endpoint]

    def reset(self):
        """Reset the server instances."""
        self.servers = {}


class MockMinioClient:
    """
    A mock Minio client for testing purposes.

    Attributes:
        _base_url (str): The endpoint URL of the Minio server.
        _access_key (str): The access key for Minio server (not used in mock).
        _secret_key (str): The secret key for Minio server (not used in mock).
        _session_token (str): The session token for Minio server (not used in mock).
        _secure (bool): Whether to use secure connection (not used in mock).
        _region (str): The region of the server (not used in mock).
        _http_client: The HTTP client to use (not used in mock).
        _credentials: The credentials object (not used in mock).
        buckets (dict): A dictionary to hold mock bucket data.
    """

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
        """
        Initialize the MockMinioClient with configuration similar to the real client.

        Args:
            endpoint (str): The endpoint URL of the Minio server.
            access_key (str, optional): The access key for Minio server.
            secret_key (str, optional): The secret key for Minio server.
            session_token (str, optional): The session token for Minio server.
            secure (bool, optional): Whether to use secure connection. Defaults to True.
            region (str, optional): The region of the server.
            http_client (optional): The HTTP client to use. Defaults to None.
            credentials (optional): The credentials object. Defaults to None.
        """
        self._base_url = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._session_token = session_token
        self._secure = secure
        self._region = region
        self._http_client = http_client
        self._credentials = credentials
        self.buckets = {}

    def connect(self, servers):
        """
        Connects the MinioMockClient to the mocked server.
        This is necessary to maintain persistency of objects across multiple initiations
        of Minio objects with the same connection string
        """
        self.buckets = servers.connect(self._base_url)

    def _health_check(self):
        if not self._base_url:
            raise ValueError("base_url is empty")
        if not validators.hostname(self._base_url) and not validators.url(
            self._base_url
        ):
            raise ValueError(f"base_url {self._base_url} is not valid")

    def fget_object(
        self,
        bucket_name,
        object_name,
        file_path,
        request_headers=None,
        ssec=None,
        version_id=None,
        extra_query_params=None,
    ):
        """
        Simulates Minio's 'fget_object' method to download an object from the mock Minio
        server and save it to a file.

        This mock method retrieves the specified object from the given bucket and writes its
        contents to the specified file path. It's a part of the MockMinioClient class that
        simulates interactions with a Minio server for testing purposes.

        Args:
            bucket_name (str): The name of the bucket containing the object to download.
            object_name (str): The name of the object to download.
            file_path (str): The path to the file where the object's data should be saved.
            request_headers (dict, optional): A dictionary of headers to send along with the
                request. Defaults to None.
            sse (optional): Server-side encryption option. Defaults to None, as it's not used in
                the mock.
            version_id (str | None, optional): The version ID of the object to download. Defaults to
                None.
            extra_query_params (dict, optional): Additional query parameters for the request.
                Defaults to None.

        Raises:
            ValueError: If the specified bucket or object doesn't exist in the mock data.
            IOError: If there's an issue writing to the specified file path.

        Returns:
            Object: Stat of the object as Object.
        """

        stat = self.stat_object(
            bucket_name,
            object_name,
            ssec,
            version_id,
        )

        the_object = self.get_object(
            bucket_name,
            object_name,
            request_headers=request_headers,
            ssec=ssec,
            version_id=version_id,
            extra_query_params=extra_query_params,
        )

        if os.path.isdir(file_path):
            raise ValueError(f"file {file_path} is a directory")

        # Create top level directory if needed.

        dirname = os.path.dirname(file_path)
        if dirname:
            try:
                os.makedirs(dirname)
            except OSError as exc:  # Python >2.5
                if exc.errno != errno.EEXIST:
                    raise

        with open(file_path, "wb") as f:
            f.write(the_object.data)

        return stat

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
        """
        Retrieves an object from the mock Minio server.

        Simulates the retrieval of an object's content from a specified bucket, allowing for
        range-based retrieval.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The name of the object to retrieve.
            offset (int, optional): The start byte position of object data to retrieve. Defaults
                to 0.
            length (int, optional): The number of bytes of object data to retrieve. Defaults to 0,
                which means the whole object.
            request_headers (dict, optional): Additional headers for the request. Defaults to None.
            ssec ( SseCustomerKey | None, optional): Server-side encryption option. Defaults to None.
            version_id (str | None, optional): The version ID of the object. Defaults to None.
            extra_query_params (dict, optional): Additional query parameters. Defaults to None.

        Returns:
            HTTPResponse: A response object containing the object data.
        """
        self._health_check()

        the_object_version = self.buckets[bucket_name].get_object(
            object_name, version_id
        )
        if not the_object_version:
            raise RuntimeError("Implementation Error")

        data = the_object_version.data

        # Create a buffer containing the data
        if isinstance(data, io.BytesIO):
            body = copy.deepcopy(data)
        elif isinstance(data, bytes):
            body = data
        elif isinstance(data, str):
            body = io.BytesIO(data.encode("utf-8"))
        else:
            body = data

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
        """
        Simulates uploading an object from a file to the mock Minio server.

        This method reads data from a specified file and uploads it as an object to a specified
        bucket.

        Args:
            bucket_name (str): The name of the bucket to upload to.
            object_name (str): The object name to create in the bucket.
            file_path (str): The path of the file to upload.
            content_type (str, optional): The content type of the object. Defaults to
                "application/octet-stream".
            metadata (dict, optional): A dictionary of additional metadata for the object. Defaults
                 to None.
            sse (optional): Server-side encryption option. Defaults to None.
            progress (optional): Callback function to monitor progress. Defaults to None.
            part_size (int, optional): The size of each part in multi-part upload. Defaults to 0.

        Returns:
            str: Confirmation message indicating successful upload.
        """
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
        part_size: int = 0,
        # num_parallel_uploads: int = 3,
        # tags = None,
        # retention = None,
        # legal_hold: bool = False,
    ):
        """
        Simulates uploading an object to the mock Minio server.

        Stores an object in a specified bucket with the given data.

        Args:
            bucket_name (str): The name of the bucket to upload to.
            object_name (str): The object name to create in the bucket.
            data: The data to upload. Can be bytes or a file-like object.
            length (int): The length of the data to upload.
            content_type (str, optional): The content type of the object. Defaults to
                "application/octet-stream".
            metadata (dict, optional): A dictionary of additional metadata for the object. Defaults
                 to None.
            sse (optional): Server-side encryption option. Defaults to None.
            progress (optional): Callback function to monitor progress. Defaults to None.
            part_size (int, optional): The size of each part in multi-part upload. Defaults to 0.

        Returns:
            str: Confirmation message indicating successful upload.
        """

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

        _ = self.buckets[bucket_name].put_object(
            object_name=object_name,
            data=data,
            length=length,
            content_type=content_type,
            metadata=metadata,
            sse=sse,
            progress=progress,
            part_size=part_size,
            # num_parallel_uploads: int = 3,
            # tags = None,
            # retention = None,
            # legal_hold: bool = False,
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
        """
        Generates a presigned URL for an object.

        Simulates the generation of a presigned URL for accessing an object. This URL can be used
        to perform the specified method (GET, PUT, etc.) on the object without further
        authentication.

        Args:
            method (str): The method to allow on the object (e.g., "GET", "PUT").
            bucket_name (str): The name of the bucket.
            object_name (str): The name of the object.
            expires (timedelta, optional): The time duration after which the presigned URL expires.
                Defaults to 7 days.
            response_headers (dict, optional): Headers to include in the response. Defaults to None.
            request_date (datetime, optional): The date of the request. Defaults to None.
            version_id (str | None, optional): The version ID of the object. Defaults to None.
            extra_query_params (dict, optional): Additional query parameters to include in the
                presigned URL. Defaults to None.

        Returns:
            str: The presigned URL.
        """
        if not version_id:
            return f"{self._base_url}/{bucket_name}/{object_name}"
        return f"{self._base_url}/{bucket_name}/{object_name}?versionId={version_id}"

    def presigned_put_object(
        self, bucket_name, object_name, expires=datetime.timedelta(days=7)
    ):
        """
        Generates a presigned URL for uploading an object.

        Provides a URL that can be used to upload an object to the specified bucket without further
        authentication.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The name of the object to upload.
            expires (timedelta, optional): The time duration after which the presigned URL expires.
                Defaults to 7 days.

        Returns:
            str: The presigned URL for the PUT operation.
        """
        return self.get_presigned_url("PUT", bucket_name, object_name, expires)

    def presigned_get_object(
        self,
        bucket_name,
        object_name,
        expires=datetime.timedelta(days=7),
        response_headers=None,
        request_date=None,
        version_id=None,
        extra_query_params=None,
    ):
        """
        Generates a presigned URL for downloading an object.

        Provides a URL that can be used to download an object from the specified bucket without
        further authentication.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The name of the object to download.
            expires (timedelta, optional): The time duration after which the presigned URL expires.
                Defaults to 7 days.
            response_headers (dict, optional): Headers to include in the response. Defaults to None.
            request_date (datetime, optional): The date of the request. Defaults to None.
            version_id (str | None, optional): The version ID of the object. Defaults to None.
            extra_query_params (dict, optional): Additional query parameters to include in the
                presigned URL. Defaults to None.

        Returns:
            str: The presigned URL for the GET operation.
        """
        return self.get_presigned_url(
            "GET",
            bucket_name,
            object_name,
            expires,
            response_headers=response_headers,
            request_date=request_date,
            version_id=version_id,
            extra_query_params=extra_query_params,
        )

    def list_buckets(self):
        """
        Lists all buckets in the mock Minio server.

        Simulates listing all the buckets available to the user in the Minio server.

        Returns:
            list: A list of bucket names.
        """
        try:
            self._health_check()
            return [
                Bucket(name, bucket._creation_date)
                for (name, bucket) in list(self.buckets.items())
            ]
        except Exception as e:
            logging.error(e)
            raise e

    def bucket_exists(self, bucket_name):
        """
        Checks if a bucket exists in the mock Minio server.

        Simulates checking for the existence of a bucket in the Minio server.

        Args:
            bucket_name (str): The name of the bucket to check.

        Returns:
            bool: True if the bucket exists, False otherwise.
        """
        self._health_check()
        try:
            self.buckets[bucket_name]
        except KeyError:
            return False
        except Exception as e:
            logging.error(e)
            raise
        return True

    def make_bucket(self, bucket_name, location=None, object_lock=False):
        """
        Creates a new bucket in the mock Minio server.

        Simulates the creation of a new bucket in the Minio server.

        Args:
            bucket_name (str): The name of the bucket to create.
            location (str, optional): The location of the bucket. Defaults to None.
            object_lock (bool, optional): Flag to enable object locking. Defaults to False.

        Returns:
            bool: True indicating the bucket was successfully created.
        """
        self._health_check()
        self.buckets[bucket_name] = MockMinioBucket(
            bucket_name=bucket_name,
            versioning=VersioningConfig(),
            location=location,
            object_lock=object_lock,
        )
        return True

    def remove_bucket(self, bucket_name: str):
        """
        Remove an empty bucket.

        :param bucket_name: Name of the bucket.

        Example::
            client.remove_bucket("my-bucket")
        """
        self._health_check()
        if bucket_name not in self.buckets:
            raise S3Error(
                code="NoSuchBucket",
                message="The specified bucket does not exist",
                resource=f"/{bucket_name}",
                request_id=None,
                host_id=None,
                response="mocked_response",
                bucket_name=bucket_name,
            )
        if self.buckets[bucket_name].objects:
            raise S3Error(
                code="BucketNotEmpty",
                message="The bucket you tried to delete is not empty",
                resource=f"/{bucket_name}",
                request_id=None,
                host_id=None,
                response="mocked_response",
                bucket_name=bucket_name,
            )
        del self.buckets[bucket_name]

    def set_bucket_versioning(self, bucket_name: str, config: VersioningConfig):
        """Bucket versioning can be set to ENABLED or SUSPENDED, but not to
        OFF (filtered out by VersioningConfig itself)
        """
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
        if not isinstance(config, VersioningConfig):
            raise ValueError("config must be VersioningConfig type")
        self.buckets[bucket_name].versioning = config

    def get_bucket_versioning(self, bucket_name: str) -> VersioningConfig:
        """Bucket versioning can be OFF (the initial value), ENABLED, or
        SUSPENDED
        """
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
        return self.buckets[bucket_name].versioning

    def list_objects(
        self,
        bucket_name,
        prefix=None,
        recursive=False,
        start_after=None,
        include_version=False,
    ):
        """
        Lists objects in a bucket with the specified prefix and conditions.

        Simulates listing objects in a bucket in the mock Minio server.

        Args:
            bucket_name (str): The name of the bucket to list objects from.
            prefix (str, optional): The prefix to filter objects by. Defaults to "".
            recursive (bool, optional): Whether to list objects recursively. Defaults to False.
            start_after (str, optional): The object name to start listing after. Defaults to "".
            include_version (bool, optional): To include the objects versions

        Returns:
            list: A list of object names, or object names and versions,
              that match the specified conditions.
        """

        try:
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
            return self.buckets[bucket_name].list_objects(
                # self.buckets,
                prefix,
                recursive,
                start_after,
                include_version,
            )
        except Exception as e:
            raise e

    def remove_object(self, bucket_name, object_name, version_id=None):
        """
        Removes an object from a bucket in the mock Minio server.

        Simulates the removal (deletion) of an object from a specified bucket.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The name of the object to remove.
            version_id (str | None, optional): The version to delete.

        Returns:
            None: The method has no return value but indicates successful removal.
        """
        self._health_check()
        return self.buckets[bucket_name].remove_object(
            object_name, version_id=version_id
        )

    def stat_object(
        self,
        bucket_name,
        object_name,
        ssec=None,
        version_id=None,
        extra_headers=None,
        extra_query_params=None,
    ) -> Object:
        """
        Get object information and metadata of an object in the mock Minio server

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The name of the object to remove.
            ssec (SseCustomerKey| None, optional): Server-side encryption customer key.
            version_id (str | None, optional): The version about which to retrieve information and metadata.
            extra_headers ( dict | None, optional ):
            extra_query_params ( dict | None, optional): Extra query parameters for advanced usage.

        Raises:
            S3Error:

        Returns:
            Object: Object information as Object.

        """
        self._health_check()

        the_stat_object = self.buckets[bucket_name].stat_object(
            object_name=object_name,
            ssec=ssec,
            version_id=version_id,
            extra_headers=extra_headers,
            extra_query_params=extra_query_params,
        )

        if not the_stat_object:
            raise RuntimeError("Implementation Error")

        return the_stat_object


@pytest.fixture
def minio_mock_servers():
    """
    Pytest fixture to yield a Servers instance.

    Yields:
        Servers: An instance of the Servers class.
    """
    yield MockMinioServers()


@pytest.fixture
def minio_mock(mocker, minio_mock_servers):
    """
    Pytest fixture to patch the Minio client with a mock.

    Args:
        mocker: The pytest-mock fixture.
        minio_mock_servers: The fixture providing a Servers instance.

    Yields:
        MockMinioClient: The patched Minio client.
    """

    def minio_mock_init(
        cls,
        *args,
        **kwargs,
    ):
        client = MockMinioClient(*args, **kwargs)
        client.connect(minio_mock_servers)
        return client

    patched = mocker.patch.object(Minio, "__new__", new=minio_mock_init)
    yield patched
