from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.security import APIKeyHeader
import httpx
import uvicorn
from db import get_partner_by_key

app = FastAPI()

TARGET_URL = "https://jsonplaceholder.typicode.com"
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

import time
from collections import defaultdict

# Simple in-memory rate limiter: {api_key: [timestamp1, timestamp2, ...]}
request_counts = defaultdict(list)

def check_rate_limit(partner: dict):
    api_key = partner['api_key']
    limit = partner['rate_limit']
    now = time.time()

    # Filter out timestamps older than 60 seconds
    request_counts[api_key] = [t for t in request_counts[api_key] if now - t < 60]

    if len(request_counts[api_key]) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    request_counts[api_key].append(now)

async def get_current_partner(api_key: str = Depends(API_KEY_HEADER)):
    if not api_key:
        raise HTTPException(status_code=403, detail="Missing API Key")

    partner = get_partner_by_key(api_key)
    if not partner:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    if not partner['active']:
        raise HTTPException(status_code=403, detail="API Key inactive")

    check_rate_limit(partner)

    return partner

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(request: Request, path: str, partner: dict = Depends(get_current_partner)):
    client = httpx.AsyncClient(base_url=TARGET_URL)

    url = httpx.URL(path=path, query=request.url.query.encode("utf-8"))

    # Forward headers, but exclude host to avoid conflicts
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None) # Let httpx handle this

    # Read body
    content = await request.body()

    try:
        rp_req = client.build_request(
            request.method,
            url,
            headers=headers,
            content=content
        )
        rp_resp = await client.send(rp_req)

        response_headers = dict(rp_resp.headers)
        response_headers.pop("content-encoding", None)
        response_headers.pop("content-length", None)

        return Response(
            content=rp_resp.content,
            status_code=rp_resp.status_code,
            headers=response_headers
        )
    finally:
        await client.aclose()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
