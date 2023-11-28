# pytest-minio-mock

## Overview
`pytest-minio-mock` is a pytest plugin designed to simplify testing of applications that interact with Minio the code  S3 compatible object storage system. It is not designed to test the correnction to the minio server. It provides a fixture that mocks the `minio.Minio` class, allowing for easy testing of Minio interactions without the need for a real Minio server.

## Features
- Mock implementation of the `minio.Minio` client.
- Easy to use pytest fixture.
- Supports common Minio operations such as bucket creation, file upload/download, etc.

## Installation

To install `pytest-minio-mock`, run:

```bash
pip install pytest-minio-mock
```

## Usage
To use the minio_mock fixture in your pytest tests, simply include it as a parameter in your test functions. Then use minio.Minio() as usual Here's an example:

```python
def test_file_upload(minio_mock):
    # Calling function foo that involves using minio.Minio()
    assert foo()
    
```

The `minio_mock` fixture will patch minio.Minio() thus providing you with a way to test your code around the Minio client easily.

## API

### MockMinioClient

A brief description of the mocked methods and their behavior, like:

`make_bucket(bucket_name, ...)` - Mocks bucket creation.
`fput_object(bucket_name, object_name, file_path, ...)` - Mocks file upload.
etc.

## Contributing
Contributions to pytest-minio-mock are welcome! The Contributing Guide is still under construction.

## License
pytest-minio-mock is licensed under the MIT License - see the LICENSE file for details.