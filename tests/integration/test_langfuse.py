"""Integration tests for Langfuse module.

Requires a running Langfuse instance. In cluster mode port-forward::

    kubectl port-forward -n langfuse svc/langfuse-web 3000:3000

And export keys::

    export LANGFUSE_SECRET_KEY=...
    export LANGFUSE_PUBLIC_KEY=...

Run::

    UNION_TEST_MODE=cluster pytest tests/integration/test_langfuse.py -v
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.langfuse]


def test_langfuse_auth_check(langfuse_client):
    """Langfuse client can authenticate against the server."""
    assert langfuse_client.health_check() is True


@pytest.mark.asyncio
async def test_langfuse_on_startup(langfuse_client):
    """Langfuse on_startup completes without errors and stays healthy."""
    await langfuse_client.on_startup()
    assert langfuse_client.health_check() is True
