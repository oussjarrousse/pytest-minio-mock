from setuptools import find_packages
from setuptools import setup


setup(
    name="pytest-minio-mock",
    entry_points={
        "pytest11": [
            "pytest_minio_mock = pytest_minio_mock.plugin",
        ],
    },
    packages=find_packages(exclude=("tests",)),
    platforms="any",
    python_requires=">=3.8",
    install_requires=["pytest>=5.0.0", "minio", "pytest-mock", "validators"],
    url="https://github.com/oussjarrousse/pytest-minio-mock",
    license="MIT",
    author="Oussama Jarrousse",
    author_email="oussama@jarrousse.org",
    description="A pytest plugin for mocking Minio S3 interactions",
    long_description=open("README.md").read(),
    keywords="pytest minio mock",
    extras_require={"dev": ["pre-commit", "tox"]},
    version="0.4.14",
    long_description_content_type="text/markdown",
    classifiers=[
        "Framework :: Pytest",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Testing",
    ],
    project_urls={
        # "Documentation": "https://pytest-minio-mock.readthedocs.io/en/latest/",
        # "Changelog": "https://pytest-minio-mock.readthedocs.io/en/latest/changelog.html",
        "Source": "https://github.com/oussjarrousse/pytest-minio-mock/",
        "Tracker": "https://github.com/oussjarrousse/pytest-minio-mock/issues",
    },
)
