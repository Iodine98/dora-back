import httpx
import pytest

from chatdoc.http_client import HttpClientFactory


@pytest.fixture(autouse=True)
def reset_shared_client():
    """
    Ensures every test starts and ends with a clean shared client, since
    ``HttpClientFactory`` keeps process-wide state.
    """
    HttpClientFactory.reset_shared_client()
    yield
    HttpClientFactory.reset_shared_client()


def test_create_client_returns_httpx_client():
    """
    Test case to verify that `create_client` returns a usable `httpx.Client`.
    """
    client = HttpClientFactory.create_client()
    try:
        assert isinstance(client, httpx.Client)
    finally:
        client.close()


def test_get_shared_client_is_singleton():
    """
    Test case to verify that `get_shared_client` always returns the same
    instance, i.e. that the HTTP client is truly shared/reused.
    """
    first = HttpClientFactory.get_shared_client()
    second = HttpClientFactory.get_shared_client()
    assert first is second


def test_reset_shared_client_creates_a_new_instance():
    """
    Test case to verify that resetting the shared client causes a brand new
    instance to be created on next access.
    """
    first = HttpClientFactory.get_shared_client()
    HttpClientFactory.reset_shared_client()
    second = HttpClientFactory.get_shared_client()
    assert first is not second


def test_verify_uses_ca_bundle_when_present(monkeypatch, tmp_path):
    """
    Test case to ensure that a configured, existing CA bundle path is used to
    verify TLS certificates (used behind the corporate proxy setup in
    `Dockerfile_with_Proxy`).
    """
    ca_bundle = tmp_path / "ca-certificates.crt"
    ca_bundle.write_text("fake-cert-contents")
    monkeypatch.setenv("REQUEST_CA_BUNDLE", str(ca_bundle))
    assert HttpClientFactory._get_verify() == str(ca_bundle)


def test_verify_defaults_to_true_when_ca_bundle_missing(monkeypatch):
    """
    Test case to ensure that TLS verification falls back to the default
    certificate store when no (valid) CA bundle is configured.
    """
    monkeypatch.delenv("REQUEST_CA_BUNDLE", raising=False)
    assert HttpClientFactory._get_verify() is True


def test_proxy_read_from_https_proxy_env(monkeypatch):
    """
    Test case to ensure the proxy is read from the `HTTPS_PROXY` environment
    variable when set.
    """
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.com:8080")
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    assert HttpClientFactory._get_proxy() == "http://proxy.example.com:8080"


def test_proxy_none_when_not_configured(monkeypatch):
    """
    Test case to ensure no proxy is used when neither `HTTP_PROXY` nor
    `HTTPS_PROXY` is set.
    """
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    assert HttpClientFactory._get_proxy() is None
