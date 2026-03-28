# Email Agent

An SMS-controlled email agent. Send an SMS from your phone to trigger actions on your email inbox.

## Architecture

```
Phone (SMS) → Mobile App → FastAPI Backend → Email Actions
```

## Roadmap

- [x] Step 1: FastAPI backend scaffold with `/health` and `/sms` endpoints
- [ ] Step 2: SMS parsing and command routing
- [ ] Step 3: Email integration (read, reply, archive, etc.)
- [ ] Step 4: Mobile app / SMS gateway integration

## Getting Started

### Prerequisites

- Python 3.11+

### Setup

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run the server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### Run tests

```bash
pytest test_main.py -v
```

## API

### `GET /health`

Returns server status.

```json
{ "status": "ok" }
```

### `POST /sms`

Receives an SMS command.

**Request body:**
```json
{
  "sender": "+1234567890",
  "message": "read inbox"
}
```

**Response:**
```json
{
  "received_from": "+1234567890",
  "message": "read inbox",
  "status": "received"
}
```
