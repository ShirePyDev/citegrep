"""Health probes.

Two endpoints on purpose:

- /healthz (liveness): "is this process alive?" It must NOT check
  dependencies. If it did, an orchestrator would restart a perfectly healthy
  app just because Qdrant was down, and a dependency outage would turn into a
  restart storm.
- /readyz (readiness): "can this process serve real work right now?" This one
  does check Qdrant, and returns 503 so load balancers stop routing traffic
  here until the dependency is back.

Qdrant itself exposes the same pair of probes, which is what /readyz calls.
"""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Response, status

from documind import __version__
from documind.config import SettingsDep

router = APIRouter(tags=["health"])


async def qdrant_ready(settings: SettingsDep) -> bool:
    """True if Qdrant answers its readiness probe within the timeout."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.qdrant_url}/readyz")
    except httpx.HTTPError:
        return False
    return resp.status_code == status.HTTP_200_OK


QdrantReadyDep = Annotated[bool, Depends(qdrant_ready)]


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/readyz")
async def readyz(qdrant_ok: QdrantReadyDep, response: Response) -> dict[str, str]:
    if not qdrant_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "qdrant": "unreachable"}
    return {"status": "ok", "qdrant": "ok"}
