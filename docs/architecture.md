# Payment Gateway Architecture Documentation

## Overview
The Payment Gateway Backend is engineered following **Clean Architecture**, **Domain-Driven Design (DDD)**, and **Hexagonal (Ports and Adapters)** architectural principles. It provides high-concurrency payment processing, idempotent request handling, atomic financial transactions, and reliable asynchronous webhook notifications via the Transactional Outbox pattern.

---

## Architectural Layers

```
                               ┌──────────────────────────────────────────┐
                               │           Presentation Layer             │
                               │  (REST Views, ViewSets, Serializers)     │
                               └────────────────────┬─────────────────────┘
                                                    │ Calls
                               ┌────────────────────▼─────────────────────┐
                               │             Service Layer                │
                               │  (Domain Business Logic & Orchestration) │
                               └─────────┬──────────────────────┬─────────┘
                                         │                      │
                   ┌─────────────────────▼───────┐      ┌───────▼─────────────────────┐
                   │       Repository Layer      │      │    Gateway Adapter Layer    │
                   │ (Data Access & Persistence) │      │  (Stripe, Razorpay, Dummy)  │
                   └─────────────────────┬───────┘      └─────────────────────────────┘
                                         │
                               ┌─────────▼────────────────────────┐
                               │           Database Layer         │
                               │     (PostgreSQL / State DB)      │
                               └──────────────────────────────────┘
```

### 1. Presentation Layer (`apps/<domain>/views.py`, `serializers.py`)
- Responsible for parsing HTTP requests, authenticating JWT bearer tokens, enforcing RBAC access permissions, validating incoming request payloads, and rendering standard JSON responses.
- Implements correlation ID propagation and idempotency replay handling via middleware and decorators.

### 2. Service Layer (`apps/<domain>/services/`)
- Contains pure business logic and orchestrates domain entities.
- Enforces state machines for Orders (`CREATED` -> `PAID` -> `CANCELLED`), Payments (`INITIATED` -> `AUTHORIZED` -> `CAPTURED` -> `FAILED`), and Refunds (`PENDING` -> `COMPLETED` -> `FAILED`).
- Manages transactional boundaries (`@transaction.atomic`).

### 3. Repository Layer (`apps/<domain>/repositories/`)
- Abstracts ORM data persistence from business logic.
- Provides clean static interfaces for query filtering, eager loading, and model mutation.

### 4. Gateway Adapter Layer (`apps/payments/adapters/`)
- Implements Hexagonal Architecture using a common interface (`BasePaymentGatewayAdapter`).
- Adapters encapsulate third-party API interactions (Stripe, Razorpay, Wallet, and Dummy).

---

## Asynchronous Architecture & Transactional Outbox

```
 [ Client Action ] ──> [ Service Layer ] ──(DB Transaction)──> [ Domain Table (Payment/Refund) ]
                                 │                                          │
                                 └───> [ Outbox Event Created ] ────────────┘
                                               │
                                       (Celery Outbox Worker)
                                               │
                                 ┌─────────────┴─────────────┐
                                 ▼                           ▼
                    [ Process Webhook Queue ]     [ Send Email Notification ]
                                 │
                     [ HTTP POST to Merchant ]
```

1. **Transactional Outbox**: When an event occurs (e.g. `payment.captured`), the event is persisted into the `OutboxEvent` database table within the **same database transaction** as the primary state change.
2. **Celery Outbox Worker**: An async Celery task picks up unprocessed events, generates HMAC-SHA256 signatures, and pushes delivery tasks to Redis/RabbitMQ queues.
3. **Dead-Letter Handling**: If a merchant endpoint returns non-2xx status codes, exponential backoff retries the delivery up to 5 times. Failed events are moved to dead-letter tracking.
