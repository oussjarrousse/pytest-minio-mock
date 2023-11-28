from setuptools import setup, find_packages


setup(
    name='pytest-minio-mock',
    version='0.1.0',
    author='Oussama Jarrousse',
    author_email='oussama@jarrousse.org',
    description='A pytest plugin for mocking Minio S3 interactions',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/oussjarrousse/pytest-minio-mock',
    packages=find_packages(),
    classifiers=[
        'Framework :: Pytest',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Testing',
    ],
    python_requires='>=3.6',
    install_requires=[
        'pytest>=5.0.0',
        'minio',
        'pytest-mock',
        'validators'
    ],
    entry_points={
        'pytest11': [
            'minio_mock = pytest_minio_mock',
        ],
    },
)