# Payment Gateway Backend

[![CI Pipeline](https://img.shields.io/github/actions/workflow/status/gaurav8299/Payment-Gateway-Backend/ci.yml?branch=main&style=flat-square&logo=github)](https://github.com/gaurav8299/Payment-Gateway-Backend/actions)
[![Coverage Status](https://img.shields.io/badge/coverage-84%25-brightgreen?style=flat-square&logo=pytest)](https://github.com/gaurav8299/Payment-Gateway-Backend)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.12-blue?style=flat-square&logo=python)](https://www.python.org)
[![Django Framework](https://img.shields.io/badge/django-5.0.7-092E20?style=flat-square&logo=django)](https://www.djangoproject.com)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ED?style=flat-square&logo=docker)](https://www.docker.com)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![Release](https://img.shields.io/badge/release-v1.0.0-blue?style=flat-square)](CHANGELOG.md)

An enterprise-grade, high-concurrency **Payment Gateway Backend** built with Django 5, Django REST Framework, PostgreSQL, Redis, Celery, and RabbitMQ. Engineered following **Clean Architecture**, **Domain-Driven Design (DDD)**, and **Hexagonal (Ports & Adapters)** principles to support multi-tenant merchant operations, atomic wallet ledgers, idempotent API requests, and transactional outbox webhooks.

---

## Key Features

- 🏛️ **Clean Architecture & SOLID**: Strict layer separation (`Presentation` -> `Service` -> `Repository` -> `Domain` -> `Adapters`).
- 🔐 **Auth & RBAC**: JWT token authentication with Blacklist invalidation, custom permissions for `ADMIN`, `MERCHANT`, and `CUSTOMER`.
- 💳 **Multi-Gateway Engine**: Polymorphic Hexagonal Adapters for Stripe, Razorpay, Wallet, and Dummy payment processors.
- 🔄 **Idempotency Guarantee**: Thread-safe Redis cache protection with `@idempotency_key_required` replay guard.
- ⚡ **Transactional Outbox & Webhooks**: Reliable webhook event publisher with HMAC-SHA256 signature verification and Celery exponential retry backoff.
- 👛 **Atomic Wallet Ledger**: High-concurrency balance transactions protected by `select_for_update()` pessimistic row locks.
- 📊 **Real-Time Analytics & Audit**: Merchant financial metrics (volume, success rate, refund rate) and immutable audit log tracing.
- 🛠️ **Developer Tooling**: Makefile commands, Postman & Insomnia collections, seed management command (`manage.py seed_data`), and complete `docs/` suite.

---

## 🏛️ System Architecture

```mermaid
graph TD
    Client[Client / Mobile / Dashboard] -->|HTTPS REST API| API[Django REST Framework]
    API --> Middleware[Correlation ID & Audit Middleware]
    Middleware --> Auth[JWT & API Key Auth Guard]
    Auth --> Service[Domain Service Layer]
    
    Service -->|Pessimistic Locks| DB[(PostgreSQL 16)]
    Service -->|Idempotency / Cache| Redis[(Redis 7)]
    Service -->|Outbox Event| Outbox[(Outbox Event Table)]
    
    Outbox -->|Async Dispatch| Celery[Celery Worker Cluster]
    Celery -->|HMAC Webhook| WebhookTarget[Merchant Webhook URL]
    Celery -->|Queue Broker| RabbitMQ[(RabbitMQ 3)]
    
    Service -->|Hexagonal Adapter| GatewayAdapter[Payment Gateway Factory]
    GatewayAdapter --> StripeAdapter[Stripe API]
    GatewayAdapter --> RazorpayAdapter[Razorpay API]
    GatewayAdapter --> WalletAdapter[Internal Wallet]
```

---

## 📊 Database Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    USERS ||--o| MERCHANT_PROFILES : "owns"
    USERS ||--o| CUSTOMER_PROFILES : "manages"
    MERCHANT_PROFILES ||--o{ MERCHANT_API_KEYS : "has"
    MERCHANT_PROFILES ||--o{ ORDERS : "receives"
    CUSTOMER_PROFILES ||--o{ ORDERS : "places"
    CUSTOMER_PROFILES ||--o| WALLETS : "holds"
    ORDERS ||--o{ PAYMENTS : "contains"
    PAYMENTS ||--o{ REFUNDS : "initiates"
    WALLETS ||--o{ WALLET_TRANSACTIONS : "records"
    MERCHANT_PROFILES ||--o{ WEBHOOK_ENDPOINTS : "configures"
```

---

## 🔄 Payment Lifecycle Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Merchant
    participant API as Payment Gateway API
    participant DB as PostgreSQL DB
    participant Gateway as External Gateway (Stripe/Razorpay)
    participant Outbox as Transactional Outbox
    participant Worker as Celery Webhook Worker

    Merchant->>API: POST /api/v1/payments/ (with Idempotency-Key)
    API->>DB: Check & acquire pessimistic lock
    API->>Gateway: Process charge request
    Gateway-->>API: Charge Success (Transaction ID)
    API->>DB: Save Payment (CAPTURED) + Save Outbox Event (payment.captured)
    API-->>Merchant: 201 Created (Payment Details)
    
    Worker->>Outbox: Poll unprocessed outbox events
    Outbox-->>Worker: Event payment.captured
    Worker->>Merchant: HTTP POST Webhook (X-Signature HMAC)
```

---

## 🖼️ User Interface & Dashboard Previews

<div align="center">
  <img src="docs/diagrams/swagger_ui.png" alt="Swagger UI API Documentation" width="900"/>
  <p><em>Interactive OpenAPI 3.0 Documentation (Swagger UI)</em></p>
</div>

<br/>

<div align="center">
  <img src="docs/diagrams/architecture_overview.png" alt="Clean Architecture & Component Isolation" width="900"/>
  <p><em>Clean Architecture & Hexagonal Adapter Components</em></p>
</div>

<br/>

<div align="center">
  <img src="docs/diagrams/docker_containers.png" alt="Docker Compose Multi-Container Orchestration" width="900"/>
  <p><em>Docker Compose Orchestration (Web, Celery, Postgres, Redis, RabbitMQ)</em></p>
</div>

<br/>

<div align="center">
  <img src="docs/diagrams/coverage_report.png" alt="Pytest Test Suite Coverage Report" width="900"/>
  <p><em>Comprehensive Pytest Coverage Report (112 Passed Tests)</em></p>
</div>

---

## 🚀 Quick Start Guide

### Option 1: Docker Compose (Recommended)

1. **Clone Repository**:
   ```bash
   git clone https://github.com/gaurav8299/Payment-Gateway-Backend.git
   cd Payment-Gateway-Backend
   ```

2. **Launch Services**:
   ```bash
   docker compose up -d --build
   ```

3. **Seed Demo Data**:
   ```bash
   docker compose exec web python manage.py seed_data
   ```

4. Access Interactive API Docs:
   - **Swagger UI**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
   - **Redoc**: [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)

---

### Option 2: Local Developer Setup (Makefile)

1. **Install Dependencies**:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Run Migrations & Seed**:
   ```bash
   make migrate
   make seed
   ```

3. **Start Development Server**:
   ```bash
   make run
   ```

4. **Run Code Quality & Test Suite**:
   ```bash
   make format
   make lint
   make test
   ```

---

## 📁 Repository Structure

```
.
├── apps/
│   ├── accounts/          # User management, Authentication & RBAC
│   ├── merchant/          # Merchant profiles, API Keys & Webhook endpoints
│   ├── customer/          # Customer CRM & Saved Payment Tokenization
│   ├── orders/            # Order creation & state machine
│   ├── payments/          # Payment engine & Hexagonal Gateway Adapters
│   ├── refunds/           # Refund engine & background retry queue
│   ├── wallet/            # Customer wallet & atomic balance ledger
│   ├── notifications/     # Notification dispatch services
│   ├── audit_logs/        # Immutable security audit logs
│   ├── webhooks/          # Transactional Outbox & HMAC delivery tasks
│   ├── analytics/         # Merchant financial dashboard aggregations
│   └── common/            # Shared base models, middleware, decorators, & commands
├── config/                # Modular Django settings (base, local, prod)
├── docs/                  # Detailed documentation suite (Architecture, API, Database, etc.)
├── tests/                 # Unit, Integration, & Concurrency Pytest suite
├── .github/               # Workflows (CI/CD), Issue Templates, PR Template, Dependabot
├── Makefile               # Shortcuts for common developer tasks
├── Dockerfile             # Multi-stage production container build
├── docker-compose.yml     # Multi-service container orchestration
├── postman_collection.json# Postman API Collection
└── insomnia_collection.json# Insomnia API Collection
```

---

## 📖 Complete Documentation Suite

For detailed technical guides, explore the [`docs/`](docs/) directory:

- 🏛️ [Architecture Guide](docs/architecture.md): Clean Architecture & Transactional Outbox pattern details.
- 📡 [API Specification](docs/api.md): Complete REST endpoint reference and request/response schemas.
- 🚀 [Deployment Guide](docs/deployment.md): Docker, Kubernetes, AWS, GCP, and Azure deployment procedures.
- 🗄️ [Database Reference](docs/database.md): Schema descriptions and entity relationships.
- ⚡ [Database Optimization](docs/database_optimization.md): Indexing strategy, query audits, and pessimistic lock analysis.
- 📝 [Logging Strategy](docs/logging.md): Correlation IDs, structured JSON logs, and data redaction.
- 📈 [Performance & Load Testing](docs/performance.md): Locust benchmarking scripts and SLAs.

---

## 📜 License & Community

- **License**: Released under the [MIT License](LICENSE).
- **Contributing**: Read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a PR.
- **Code of Conduct**: We adhere to the [Contributor Code of Conduct](CODE_OF_CONDUCT.md).
- **Security**: Report security vulnerabilities safely following our [Security Policy](SECURITY.md).
