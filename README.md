# API Manager Gateway POC

This project implements a secure API Gateway that sits between external partners and internal services (simulated by [JSONPlaceholder](https://jsonplaceholder.typicode.com)).

## Features

- **Authentication**: Validates `X-API-Key` headers against a SQLite database.
- **Rate Limiting**: Enforces request limits per minute per partner (Sliding Window).
- **Access Control**: Restricts partners to specific resources (e.g., `/posts`, `/users`).
- **Usage Tracking**: Logs all request details (partner, timestamp, path, status) to the database.
- **Proxying**: Transparently forwards requests to the backend service.

## Architecture

- **Language**: Python 3.12+
- **Framework**: FastAPI (ASGI)
- **Server**: Uvicorn
- **HTTP Client**: httpx (Async)
- **Database**: SQLite (local `gateway.db`)

See [DESIGN.md](DESIGN.md) for architecture details.

## Setup & Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Database**
   This script creates the `partners`, `permissions`, and `api_usage` tables and seeds them with test data.
   ```bash
   python init_db.py
   ```

   **Default Test Keys:**
   - **Partner A** (`key_a`): Limit 10/min, Access to `/posts`
   - **Partner B** (`key_b`): Limit 5/min, Access to `/users`
   - **God Mode** (`god_mode`): Limit 1000/min, Access to `/` (everything)

## Usage

1. **Start the Server**
   ```bash
   python main.py
   ```
   The server runs on `http://0.0.0.0:8000`.

2. **Make Requests**
   ```bash
   # Partner A accessing posts (Allowed)
   curl -H "X-API-Key: key_a" http://localhost:8000/posts/1

   # Partner A accessing users (Denied - 403)
   curl -H "X-API-Key: key_a" http://localhost:8000/users/1
   ```

## Testing

Run the integration test suite:
```bash
python test_gateway.py
```
This runs scenarios for:
- Missing/Invalid Keys
- Valid Proxying
- Rate Limit Enforcement
- Permission Enforcement
- Usage Logging
