from collections.abc import Callable, Iterable
from typing import Any, SupportsBytes, SupportsIndex

from _typeshed import ReadableBuffer
from authlib.oauth2.client import OAuth2Client as _OAuth2Client
from httpx import Client
from httpx._client import UseClientDefault
from httpx._types import AuthTypes, HeaderTypes

class OAuth2Client(_OAuth2Client, Client):
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        token_endpoint_auth_method: str | None = None,
        revocation_endpoint_auth_method: str | None = None,
        scope: str | None = None,
        redirect_uri: str | None = None,
        token: dict[str, object] | None = None,
        token_placement: str = "header",  # noqa: S107
        update_token: Callable[[dict[str, object], str | None, str | None], None] | None = None,
        **kwargs: object,
    ) -> None: ...
    def create_authorization_url(
        self,
        url: str,
        state: str | None = None,
        code_verifier: str | bytes | float | Iterable[SupportsIndex] | SupportsIndex | SupportsBytes | ReadableBuffer | None = None,
        **kwargs: object,
    ) -> tuple[str, str]: ...
    def fetch_token(
        self,
        url: str | None = None,
        body: str = "",
        method: str = "POST",
        headers: HeaderTypes | None = None,
        auth: AuthTypes | UseClientDefault | None = None,
        grant_type: str | None = None,
        state: str | None = None,
        **kwargs: object,
    ) -> dict[Any, Any]: ...
