# Security Policy

## Supported Versions

Only the latest release version is supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of our Payment Gateway Backend very seriously. If you believe you have found a security vulnerability in this project, please report it to us immediately.

**Do NOT report security vulnerabilities via public GitHub issues.**

Please email your report to `security@paymentgateway.internal` with:
- Type of issue (e.g. SQL injection, HMAC bypass, XSS, unauthorized access)
- Step-by-step instructions to reproduce the issue
- Affected endpoint(s) or component(s)
- Proof of concept or example payload if available

## Security Protections Implemented
- **Secret Key Hashing**: All API secret keys and webhook secrets are stored as SHA256 hashes.
- **HMAC SHA256 Webhook Signatures**: All outgoing webhooks carry a signed signature header (`X-Signature`).
- **Idempotency Protection**: Redundant requests with identical `Idempotency-Key` headers are safely cached and replayed without re-executing state transitions.
- **Atomic Balance Locking**: Wallet updates utilize `select_for_update()` pessimistic locks to eliminate race conditions.
- **Strict Network Isolation**: Internal Celery queues and Redis caches operate within isolated networks in production.
