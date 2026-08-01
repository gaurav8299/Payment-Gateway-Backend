# Payment Gateway Deployment Guide

## Overview
This document outlines production deployment strategies for the Payment Gateway Backend across Docker Compose, Kubernetes, and Cloud Container Platforms (AWS ECS, GCP Cloud Run, Azure App Service).

---

## 1. Local / On-Premise Deployment (Docker Compose)

### Architecture
The container setup consists of 5 services:
1. `web`: Gunicorn WSGI server running Django application.
2. `celery_worker`: Background process processing webhooks, email notifications, and outbox retries.
3. `celery_beat`: Cron scheduler for periodic tasks (e.g. daily summaries, stale order cleanup).
4. `db`: PostgreSQL 16 relational database with persistent volume.
5. `redis`: In-memory cache, Celery result backend, and idempotency key lock manager.

### Command Execution
```bash
# Clone repository
git clone https://github.com/your-org/payment-gateway-backend.git
cd payment-gateway-backend

# Configure production environment variables
cp .env.example .env

# Build and launch containers
docker compose up -d --build

# Verify container health
docker compose ps

# Seed demo data (optional)
docker compose exec web python manage.py seed_data
```

---

## 2. Cloud Production Deployment (AWS ECS / GCP / Azure)

### Environment Prerequisites
- Managed PostgreSQL (AWS RDS PostgreSQL 16 / GCP Cloud SQL).
- Managed Redis (AWS ElastiCache Redis / GCP Memorystore).
- Managed Message Broker (RabbitMQ / AWS SQS).
- SSL Termination & Reverse Proxy (AWS ALB / NGINX / Cloudflare).

### Secret Management
Ensure production environment variables (`SECRET_KEY`, `DB_PASSWORD`, `WEBHOOK_SIGNING_KEY`) are fetched from Cloud Secret Managers (AWS Secrets Manager / GCP Secret Manager / Vault). Never commit plain `.env` files.
