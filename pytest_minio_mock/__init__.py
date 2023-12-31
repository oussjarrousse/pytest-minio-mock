"""
A pytest plugin for mocking Minio S3 interactions. This module provides a mock Minio client and
server setup to facilitate testing of applications that interact with Minio S3 storage without the
need for a real Minio server. It's designed to mimic the behavior of the real Minio client to a
degree that is useful for testing purposes.

Usage:
    Import the required fixtures and mock classes directly from this package in your test suite to
    mock Minio interactions.

Note:
    This package should be used for testing purposes only and not in a production environment.

For more information and usage examples, please refer to the project's README.md.

"""

__version__ = "0.1.9"
__author__ = "Oussama Jarrousse"
