# pytest-minio-mock

### Pip Stats
[![PyPI version](https://badge.fury.io/py/pytest-minio-mock.svg)](https://badge.fury.io/py/pytest-minio-mock)
[![Downloads](https://static.pepy.tech/badge/pytest-minio-mock)](https://pepy.tech/project/pytest-minio-mock)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)

## Overview
`pytest-minio-mock` is a pytest plugin designed to simplify testing of applications that interact with Minio the code  S3 compatible object storage system. It is not designed to test the correnction to the minio server. It provides a fixture that mocks the `minio.Minio` class, allowing for easy testing of Minio interactions without the need for a real Minio server.

The plugin supports python version 3.8 or above.

## Features
- Mock implementation of the `minio.Minio` client.
- Easy to use pytest fixture.
- Supports versioning.
- Currently the plugin mocks the following Minio client APIs:

    **Bucket Operations:**
  
    - `make_bucket`
    - `list_buckets`
    - `bucket_exists`
    - `remove_bucket`
    - `list_objects`
    - `get_bucket_versioning`
    - `set_bucket_versioning`
    
    **Objects Operations:**
    
    - `get_object`
    - `fget_object`
    - `put_object`
    - `fput_object`
    - `stat_object`
    - `remove_object`
    - `get_presigned_url`
    - `presigned_put_object`
    - `presigned_get_object`

## Installation

To install `pytest-minio-mock`, run:

```bash
pip install pytest-minio-mock
```

## Usage
To use the minio_mock fixture in your pytest tests, simply include it as a parameter in your test functions. Then use minio.Minio() as usual Here's an example:

```python
def foo():
    try:
        minio_client = minio.Minio(
            endpoint=S3_URI,
            access_key=S3_ACCESS_KEY,
            secret_key=S3_SECRET_KEY,
            region=S3_REGION
        )
        return minio_client.make_bucket("buckets")
    except Exception as e:
        logging.error(e)


def test_file_upload(minio_mock):
    # Calling function foo that involves using minio.Minio()
    assert foo()
    minio_client = minio.Minio(
            endpoint=S3_URI,
            access_key=S3_ACCESS_KEY,
            secret_key=S3_SECRET_KEY,
            region=S3_REGION
        )
    buckets = minio.list_buckets()
    assert len(buckets)==1

```

The `minio_mock` fixture will patch newly created minio.Minio() thus providing you with a way to test your code around the Minio client easily.

At the moment, instances of minio.Minio() created before loading the minio_mock fixture code will not be patched. This might be an issue if one or more of the fixtures you are using in your tests that preceeds `minio_mock` in the parameters list of the test function, initiates instances of minio.Minio() that you want to test. As a workaround make sure that minio_mock is the first fixture in the list of arguments of function where minio_mock is needed. Example:

```python
@pytest.fixture()
def system_under_test(minio_mock: MockMinioClient, storage_provider_stub: StorageProvider):
    # your code here
    pass
```

## API

### MockMinioClient

A brief description of the mocked methods and their behavior, like:

- `make_bucket(bucket_name, ...)` # Mocks bucket creation.
- `fput_object(bucket_name, object_name, file_path, ...)` # Mocks file upload.
- ...


## Contributing
Contributions to pytest-minio-mock are welcome!

Follow the usual path:
 - fork the repository
 - create a feature branch
 - push the branch to your forked repository
 - from the forked repository, create a "pull request" to this project.

When creating a pull request make sure to use the following template:

```
Change Summary
 - item one
 - item two
Related issue number
 - issue a
 - issue b
Checklist
  [ ] code is ready
  [ ] add tests
  [ ] all tests passing
  [ ] test coverage did not drop
  [ ] PR is ready for review
```

After a pull request has been submitted:
- A reviewer must review the pull-request
- the pull requests must pass all tests for all supported python versions 3.8, 3.9, 3.10, 3.11 and 3.12.
- A maintainer will eventually merges the pull request
- A release manager will upload it to pypi.

## License
pytest-minio-mock is licensed under the MIT License - see the LICENSE file for details.
