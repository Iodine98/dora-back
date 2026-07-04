"""
==========================================================================
        Module: HTTP Client Factory
==========================================================================

Provides a single, reusable HTTP client (``httpx.Client``) that is shared
by every component talking to an external HTTP API (e.g. the OpenAI API).

Before this module existed, every call site that needed to talk to an
external vendor API (``ChatModel``, ``EmbeddingFactory``, ...) relied on
the vendor SDK creating its own ad-hoc ``httpx``/``requests`` client under
the hood. That made it impossible to consistently configure proxy
settings, custom CA bundles and timeouts in one place (see
``Dockerfile_with_Proxy``, which builds/runs this app behind a corporate
proxy with a custom CA bundle).

``HttpClientFactory`` centralizes that configuration and exposes a single
process-wide client via :meth:`HttpClientFactory.get_shared_client`, while
still allowing callers to inject their own client (e.g. in tests) via
dependency injection.
"""

import os
from typing import Optional, Union

import httpx

DEFAULT_TIMEOUT_SECONDS = 60.0


class HttpClientFactory:
    """
    Factory responsible for creating and sharing a single, configurable
    ``httpx.Client`` instance.

    Attributes:
        _shared_client (Optional[httpx.Client]): Lazily-created, process-wide
            HTTP client instance.
    """

    _shared_client: Optional[httpx.Client] = None

    @staticmethod
    def _get_proxy() -> Optional[str]:
        """
        Reads the proxy to use (if any) from the standard ``HTTPS_PROXY``/
        ``HTTP_PROXY`` environment variables.

        Returns:
            Optional[str]: The proxy URL, or ``None`` if no proxy is configured.
        """
        return os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or None

    @staticmethod
    def _get_verify() -> Union[bool, str]:
        """
        Determines the TLS verification setting for the client.

        If a custom CA bundle is configured (e.g. via ``REQUEST_CA_BUNDLE``,
        used by ``Dockerfile_with_Proxy``) and the file exists, it is used to
        verify the TLS certificates. Otherwise, the default certificate
        store is used.

        Returns:
            Union[bool, str]: The path to a CA bundle, or ``True`` to use the
                default certificate store.
        """
        ca_bundle = os.environ.get("REQUEST_CA_BUNDLE")
        if ca_bundle and os.path.isfile(ca_bundle):
            return ca_bundle
        return True

    @classmethod
    def create_client(cls, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> httpx.Client:
        """
        Creates a new, independently configured ``httpx.Client``.

        Args:
            timeout (float, optional): The request timeout in seconds.
                Defaults to ``DEFAULT_TIMEOUT_SECONDS``.

        Returns:
            httpx.Client: A newly created HTTP client.
        """
        client_kwargs: dict = {
            "timeout": timeout,
            "verify": cls._get_verify(),
        }
        proxy = cls._get_proxy()
        if proxy:
            client_kwargs["proxy"] = proxy
        return httpx.Client(**client_kwargs)

    @classmethod
    def get_shared_client(cls) -> httpx.Client:
        """
        Returns the process-wide shared ``httpx.Client``, creating it lazily
        on first use.

        Returns:
            httpx.Client: The shared HTTP client instance.
        """
        if cls._shared_client is None:
            cls._shared_client = cls.create_client()
        return cls._shared_client

    @classmethod
    def reset_shared_client(cls) -> None:
        """
        Closes (if open) and clears the shared client.

        Mainly useful for tests that need a clean slate between runs.
        """
        if cls._shared_client is not None:
            cls._shared_client.close()
        cls._shared_client = None
