# Payment Gateway API Specification

## General Information
- **Base URL**: `http://localhost:8000/api/v1`
- **Interactive Documentation**: Swagger UI at `http://localhost:8000/api/docs/`, Redoc at `http://localhost:8000/api/redoc/`
- **Authentication**: HTTP Bearer JWT (`Authorization: Bearer <access_token>`) or Merchant Secret API Key (`X-Api-Key: sk_live_...`).

---

## Core Endpoints Summary

| Module | Method | Endpoint | Description | Auth Required |
| ------ | ------ | -------- | ----------- | ------------- |
| **Auth** | `POST` | `/api/v1/auth/register/` | Register User/Merchant account | No |
| **Auth** | `POST` | `/api/v1/auth/login/` | Obtain JWT Access and Refresh Tokens | No |
| **Auth** | `POST` | `/api/v1/auth/token/refresh/` | Refresh expired JWT token | No |
| **Merchant** | `GET` | `/api/v1/merchant/profile/` | Retrieve merchant business profile | Yes (`MERCHANT`) |
| **Merchant** | `POST` | `/api/v1/merchant/api-keys/` | Generate publishable/secret API key pair | Yes (`MERCHANT`) |
| **Customer** | `GET` | `/api/v1/customers/` | List registered merchant customers | Yes (`MERCHANT`) |
| **Customer** | `POST` | `/api/v1/customers/` | Create a customer profile | Yes (`MERCHANT`) |
| **Orders** | `POST` | `/api/v1/orders/` | Create a new payment order | Yes |
| **Orders** | `GET` | `/api/v1/orders/` | List orders with pagination & filters | Yes |
| **Payments** | `POST` | `/api/v1/payments/` | Initiate / Capture payment transaction | Yes |
| **Payments** | `GET` | `/api/v1/payments/` | List payment transactions | Yes |
| **Refunds** | `POST` | `/api/v1/refunds/` | Initiate full or partial refund | Yes |
| **Refunds** | `GET` | `/api/v1/refunds/` | List refund operations | Yes |
| **Wallet** | `GET` | `/api/v1/wallets/me/` | Get current customer wallet balance | Yes (`CUSTOMER`) |
| **Wallet** | `POST` | `/api/v1/wallets/topup/` | Top-up customer wallet balance | Yes (`CUSTOMER`) |
| **Webhooks** | `POST` | `/api/v1/webhooks/endpoints/` | Register merchant webhook callback URL | Yes (`MERCHANT`) |
| **Analytics**| `GET` | `/api/v1/analytics/overview/` | Real-time merchant revenue & transaction metrics | Yes (`MERCHANT`) |
| **Audit** | `GET` | `/api/v1/audit-logs/` | Query security audit events | Yes (`ADMIN`/`MERCHANT`) |

---

## Standard Error Response Format

All error responses return standard HTTP status codes along with a structured JSON body:

```json
{
  "error": {
    "code": "INVALID_STATE_TRANSITION",
    "message": "Payment in state 'FAILED' cannot be refunded.",
    "details": {},
    "timestamp": "2026-08-01T12:00:00Z"
  }
}
```

---

## Idempotency Key Usage
Pass an `Idempotency-Key: <unique_string>` header on mutating requests (`POST /orders/`, `POST /payments/`, `POST /refunds/`). Subsequent identical requests return the cached response without re-executing business logic.
