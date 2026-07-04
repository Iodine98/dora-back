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
process-wide client via :meth:`HttpClientFactory.get_shared_client` (and
its async counterpart, :meth:`HttpClientFactory.get_shared_async_client`,
since vendor SDKs such as the OpenAI SDK maintain separate sync/async
HTTP clients), while still allowing callers to inject their own client
(e.g. in tests) via dependency injection.
"""

import os
from typing import Optional, Union

import httpx

DEFAULT_TIMEOUT_SECONDS = 60.0


class HttpClientFactory:
    """
    Factory responsible for creating and sharing a single, configurable
    ``httpx.Client``/``httpx.AsyncClient`` instance.

    Attributes:
        _shared_client (Optional[httpx.Client]): Lazily-created, process-wide
            HTTP client instance.
        _shared_async_client (Optional[httpx.AsyncClient]): Lazily-created,
            process-wide async HTTP client instance.
    """

    _shared_client: Optional[httpx.Client] = None
    _shared_async_client: Optional[httpx.AsyncClient] = None

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
    def _build_client_kwargs(cls, timeout: float) -> dict:
        client_kwargs: dict = {
            "timeout": timeout,
            "verify": cls._get_verify(),
        }
        proxy = cls._get_proxy()
        if proxy:
            client_kwargs["proxy"] = proxy
        return client_kwargs

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
        return httpx.Client(**cls._build_client_kwargs(timeout))

    @classmethod
    def create_async_client(cls, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> httpx.AsyncClient:
        """
        Creates a new, independently configured ``httpx.AsyncClient``.

        Args:
            timeout (float, optional): The request timeout in seconds.
                Defaults to ``DEFAULT_TIMEOUT_SECONDS``.

        Returns:
            httpx.AsyncClient: A newly created async HTTP client.
        """
        return httpx.AsyncClient(**cls._build_client_kwargs(timeout))

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
    def get_shared_async_client(cls) -> httpx.AsyncClient:
        """
        Returns the process-wide shared ``httpx.AsyncClient``, creating it
        lazily on first use.

        Returns:
            httpx.AsyncClient: The shared async HTTP client instance.
        """
        if cls._shared_async_client is None:
            cls._shared_async_client = cls.create_async_client()
        return cls._shared_async_client

    @classmethod
    def reset_shared_client(cls) -> None:
        """
        Closes (if open) and clears the shared sync and async clients.

        Mainly useful for tests that need a clean slate between runs.
        """
        if cls._shared_client is not None:
            cls._shared_client.close()
        cls._shared_client = None
        if cls._shared_async_client is not None:
            # Closing an async client requires an event loop; since we don't
            # want to force one here, just drop the reference and let the
            # garbage collector reclaim it. This mirrors the "best effort"
            # cleanup approach used elsewhere for async resources.
            cls._shared_async_client = None
