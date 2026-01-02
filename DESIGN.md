# API Gateway Design

## Overview
This project implements an API Gateway to manage access to internal services (simulated by JSONPlaceholder). It provides:
- **Authentication**: API Key validation.
- **Rate Limiting**: Limits the number of requests per minute per partner.
- **Proxying**: Forwards valid requests to the backend service.

## Architecture

### Components
1. **Client**: External partners making HTTP requests.
2. **API Gateway (FastAPI)**:
   - Catches all requests.
   - Validates `X-API-Key`.
   - Checks rate limits.
   - Forwards request to JSONPlaceholder using `httpx`.
   - Returns the response to the client.
3. **Database (SQLite)**: Stores partner information and access rules.

### Database Schema

**Table: `partners`**
- `id` (INTEGER PRIMARY KEY)
- `name` (TEXT)
- `api_key` (TEXT UNIQUE)
- `active` (BOOLEAN)
- `rate_limit` (INTEGER) - Requests per minute.

### Request Flow
1. Client sends `GET /posts` with header `X-API-Key: abc`.
2. Gateway middleware/dependency:
   - Queries DB for `api_key='abc'`.
   - If not found or inactive -> Returns `403 Forbidden`.
   - Checks in-memory rate limiter for key 'abc'.
   - If limit exceeded -> Returns `429 Too Many Requests`.
3. Gateway Proxy:
   - Rewrites URL to `https://jsonplaceholder.typicode.com/posts`.
   - Forwards request.
4. Gateway receives response and streams it back to Client.
