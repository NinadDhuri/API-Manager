from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.security import APIKeyHeader
import httpx
import uvicorn
from db import get_partner_by_key, get_permissions, log_usage

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

def check_permissions(partner: dict, path: str):
    api_key = partner['api_key']
    allowed_resources = get_permissions(api_key)

    # Check if path starts with any allowed resource
    # Ensure path starts with / for comparison
    normalized_path = "/" + path if not path.startswith("/") else path

    has_permission = False
    for resource in allowed_resources:
        if normalized_path.startswith(resource):
            has_permission = True
            break

    if not has_permission:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

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
    # Check permissions
    check_permissions(partner, path)

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
        # Log usage
        # Note: In a real app, this should be a background task or middleware
        # to avoid blocking/failing the response if logging fails.
        # But we need status_code from response, which we have in `rp_resp` if successful.
        # If exception occurred, we might not log or log 500.
        try:
             status = rp_resp.status_code if 'rp_resp' in locals() else 500
             log_usage(
                partner['id'],
                partner['api_key'],
                time.time(),
                request.method,
                "/" + path,
                status
             )
        except Exception as e:
            print(f"Failed to log usage: {e}")

        await client.aclose()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
