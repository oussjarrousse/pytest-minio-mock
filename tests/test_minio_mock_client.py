"""
"""
import pytest

from pytest_minio_mock.plugin import MockMinioClient


@pytest.mark.UNIT
class TestsMockMinioClient:
    @pytest.mark.parametrize("is_secure", [True, False])
    @pytest.mark.UNIT
    def test_mock_minio_client_init_without_endpoint_schema_and_with_minimal_parameters(
        self, is_secure: bool
    ):
        endpoint = "localhost:9000"
        client = MockMinioClient(endpoint, secure=is_secure)

        base_url_schema = "https" if is_secure else "http"
        assert client._base_url == f"{base_url_schema}://{endpoint}"
        assert client._access_key is None
        assert client._secret_key is None
        assert client._session_token is None
        assert client._secure is is_secure
        assert client._region is None
        assert client._http_client is None
        assert client._credentials is None
        assert client._cert_check is True

    @pytest.mark.UNIT
    def test_mock_minio_client_init_with_minimal_parameters(self):
        endpoint = "https://localhost:9000"
        client = MockMinioClient(endpoint)
        assert client._base_url == endpoint
        assert client._access_key is None
        assert client._secret_key is None
        assert client._session_token is None
        assert client._secure is True
        assert client._region is None
        assert client._http_client is None
        assert client._credentials is None
        assert client._cert_check is True

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
        cert_check = False

        client = MockMinioClient(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            secure=secure,
            region=region,
            http_client=http_client,
            credentials=credentials,
            cert_check=cert_check,
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
        assert client._cert_check == cert_check

    @pytest.mark.UNIT
    def test_mock_minio_client_init_error_handling(self):
        with pytest.raises(
            TypeError, match="missing 1 required positional argument: 'endpoint'"
        ):
            MockMinioClient()  # not passing endpoint should raise an error

    @pytest.mark.parametrize(
        "endpoint",
        [
            "http://localhost:9000",
            "https://localhost:9000",
            "localhost:9000",
            "any-endpoint.local",
        ],
    )
    @pytest.mark.UNIT
    def test_mock_minio_client_health_check(self, endpoint: str):
        client = MockMinioClient(endpoint)
        assert client._health_check() is None
