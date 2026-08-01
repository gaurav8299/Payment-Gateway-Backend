# Changelog

All notable changes to the Payment Gateway Backend project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-01

### Added
- **Clean Architecture & SOLID Foundation**: Domain models, Hexagonal Repository Pattern, Service Layer abstractions.
- **Authentication & RBAC**: JWT authentication with Refresh Tokens, Role-Based Access Control (`ADMIN`, `MERCHANT`, `CUSTOMER`).
- **Merchant Management**: Merchant profiles, business categorization, publishable/secret API Key management with SHA256 hashing.
- **Customer CRM & Wallets**: Customer management, tokenized saved payment methods (cards/UPI), multi-currency wallet ledger with atomic transactions.
- **Orders & Payments Engine**: State-machine driven order/payment lifecycle (`INITIATED`, `AUTHORIZED`, `CAPTURED`, `FAILED`), multi-gateway support (Razorpay, Stripe, Dummy, Wallet).
- **Refund Engine**: Full & partial refunds, asynchronous retry queue, state transitions (`PENDING`, `COMPLETED`, `FAILED`).
- **Transactional Outbox & Webhooks**: Reliable webhook event publisher, HMAC-SHA256 signature calculation, retry backoff with dead-letter queue.
- **Real-Time Analytics & Audit Logs**: Merchant financial metrics (volume, success rate, refund rate), structured correlation ID logging and immutable audit logs.
- **Developer Experience & Tooling**: Postman and Insomnia API Collections, Makefile, `seed_data` management command, expanded pre-commit hooks, GitHub Issue/PR templates, and Dependabot config.
- **Comprehensive Documentation**: Complete `docs/` suite covering Architecture, OpenAPI specifications, Deployment, Database Schema & Optimization, Logging Strategy, and Performance Benchmarking.
