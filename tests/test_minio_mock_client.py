"""
"""
import pytest

from pytest_minio_mock.plugin import MockMinioClient


@pytest.mark.UNIT
class TestsMockMinioClient:
    @pytest.mark.UNIT
    def test_mock_minio_client_init_with_minimal_parameters(self):
        endpoint = "http://localhost:9000"
        client = MockMinioClient(endpoint)
        assert client._base_url == endpoint
        assert client._access_key == None
        assert client._secret_key == None
        assert client._session_token == None
        assert client._secure is True
        assert client._region == None
        assert client._http_client == None
        assert client._credentials == None

    @pytest.mark.UNIT
    def test_mock_minio_client_init_with_all_params(self):
        endpoint = "http://localhost:9000"
        access_key = "accessKey"
        secret_key = "secretKey"
        session_token = "sessionToken"
        secure = False
        region = "us-east-1"
        http_client = "mock_http_client"
        credentials = "mock_credentials"

        client = MockMinioClient(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            secure=secure,
            region=region,
            http_client=http_client,
            credentials=credentials,
        )

        assert client._base_url == endpoint, "Endpoint should be stored correctly"
        assert client._access_key == access_key, "Access key should be stored correctly"
        assert client._secret_key == secret_key, "Secret key should be stored correctly"
        assert (
            client._session_token == session_token
        ), "Session token should be stored correctly"
        assert client._secure == secure, "Secure should reflect the passed value"
        assert client._region == region, "Region should be stored correctly"
        assert (
            client._http_client == http_client
        ), "HTTP client should be stored correctly"
        assert (
            client._credentials == credentials
        ), "Credentials should be stored correctly"

    @pytest.mark.UNIT
    def test_mock_minio_client_init_error_handling(self):
        with pytest.raises(
            TypeError, match="missing 1 required positional argument: 'endpoint'"
        ):
            client = MockMinioClient()  # not passing endpoint should raise an error
