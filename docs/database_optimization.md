# Database Optimization & Query Audit Report

## Executive Summary
This report details database index coverage, query optimization strategies, N+1 query elimination, and concurrency locking mechanisms implemented across the Payment Gateway Backend.

---

## 1. Indexing Strategy

### Compound & Single-Column Indexes
Strategic indexes were added to eliminate full table scans during high-throughput queries:

| Table | Index Columns | Purpose | Query Optimization |
| ----- | ------------- | ------- | ------------------ |
| `payments` | `(merchant_id, status, created_at)` | Merchant dashboard pagination & time filtering | `O(log N)` range scans |
| `payments` | `(order_id, status)` | Payment lookup during order fulfillment | Instant lookup |
| `payments` | `(gateway, gateway_transaction_id)` | Webhook callback reconciliation | Instant match |
| `refunds` | `(payment_id, status)` | Refund eligibility & total refunded aggregation | Prevents full table scan |
| `wallets` | `(customer_id, merchant_id, currency)` | Unique wallet resolution | `O(1)` fetch |
| `outbox_events` | `(processed, created_at)` | Celery outbox polling worker | Immediate fetch of unhandled events |

---

## 2. N+1 Query Elimination

### Best Practices Applied
- **`select_related`**: Used for single-valued relationships (e.g. `Payment.objects.select_related("merchant", "order", "customer")`).
- **`prefetch_related`**: Used for multi-valued relationships (e.g. `MerchantProfile.objects.prefetch_related("api_keys", "merchant_webhook_configs")`).

---

## 3. Concurrency & Locking Strategy

### Pessimistic Locking (`select_for_update()`)
To prevent double-spending and race conditions during simultaneous payment charges or balance debits:
- **Wallet Debits**: `Wallet.objects.select_for_update().get(id=wallet_id)` acquires an exclusive row-level lock within `@transaction.atomic`.
- **Payment Processing**: Locks payment records prior to applying state updates.
