# Logging Strategy & Audit Logging Documentation

## Overview
The Payment Gateway Backend implements structured JSON logging, correlation ID tracing, audit logging for compliance, and distinct log streams for background Celery workers and webhook deliveries.

---

## 1. Correlation ID Tracing (`CorrelationIDMiddleware`)
- Every incoming HTTP request is assigned a unique `X-Correlation-ID` header (or reads the existing correlation header sent by upstream microservices/load balancers).
- The correlation ID is stored in thread-local storage via `common.middleware.CorrelationIDFilter` and automatically injected into every log record.

### Log Format
```
{levelname} {asctime} [{name}] [Correlation-ID: {correlation_id}] {message}
```

---

## 2. Log Categories & Handlers

| Stream | Logger Name | Target | Purpose |
| ------ | ----------- | ------ | ------- |
| **Application Log** | `payment_gateway` | stdout / `logs/app.log` | API requests, state machine transitions, errors |
| **Celery Tasks** | `celery.task` | stdout / `logs/celery.log` | Background outbox processing, webhook delivery retries |
| **Webhook Delivery**| `webhooks.delivery` | stdout / `logs/webhooks.log` | HTTP POST attempts to merchant callback endpoints |
| **Audit Trail** | `audit_logs` | Database (`AuditLog` table) | Immutable security & administrative event log |

---

## 3. Data Sanitization & Sensitive Field Redaction
Logs automatically redact sensitive fields to maintain PCI-DSS compliance:
- Passwords, JWT tokens, and API secret keys are scrubbed.
- Credit card numbers are masked showing only the last 4 digits (`4242 **** **** 4242`).
