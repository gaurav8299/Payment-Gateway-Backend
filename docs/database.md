# Payment Gateway Database Schema & Entity Relationships

## Database Architecture
The backend uses **PostgreSQL 16** with strong ACID guarantees, foreign keys, transaction isolation, and strategic b-tree indexes.

---

## Core Entities & Tables

### 1. Users (`users`)
- Stores system identity records (`ADMIN`, `MERCHANT`, `CUSTOMER`).
- Fields: `id` (UUID), `email` (Unique Index), `password`, `role`, `is_active`, `created_at`, `updated_at`.

### 2. Merchant Profiles (`merchant_profiles`)
- Business entities owning payment operations and API keys.
- Fields: `id` (UUID), `user_id` (FK), `business_name`, `status` (`PENDING`, `ACTIVE`, `SUSPENDED`), `currency`, `gst_number`, `pan_number`.

### 3. Merchant API Keys (`merchant_api_keys`)
- Credentials used for API access.
- Fields: `id` (UUID), `merchant_id` (FK), `name`, `publishable_key` (Index), `hashed_secret_key` (Index), `is_active`.

### 4. Customer Profiles (`customer_profiles`)
- Customers registered under a specific merchant.
- Fields: `id` (UUID), `merchant_id` (FK), `email` (Index), `name`, `phone`.

### 5. Wallets & Transactions (`wallets`, `wallet_transactions`)
- Customer store of value and ledger entries.
- Fields (`wallets`): `id` (UUID), `customer_id` (FK), `merchant_id` (FK), `balance` (Decimal), `currency`.
- Fields (`wallet_transactions`): `id` (UUID), `wallet_id` (FK), `amount`, `type` (`CREDIT`, `DEBIT`), `reference`.

### 6. Orders (`orders`)
- Invoice/Order records created prior to payment.
- Fields: `id` (UUID), `order_number` (Unique Index), `merchant_id` (FK), `customer_id` (FK), `amount`, `currency`, `status` (`CREATED`, `PAID`, `CANCELLED`).

### 7. Payments (`payments`)
- Financial transactions executed against an order.
- Fields: `id` (UUID), `payment_id` (Unique Index), `merchant_id` (FK), `order_id` (FK), `customer_id` (FK), `amount`, `currency`, `status` (`INITIATED`, `AUTHORIZED`, `CAPTURED`, `FAILED`, `REFUNDED`), `gateway`, `gateway_transaction_id`.

### 8. Refunds (`refunds`)
- Full or partial money returns executed against a payment.
- Fields: `id` (UUID), `refund_id` (Unique Index), `payment_id` (FK), `merchant_id` (FK), `amount`, `currency`, `status` (`PENDING`, `COMPLETED`, `FAILED`), `reason`.

### 9. Outbox & Webhooks (`outbox_events`, `webhook_endpoints`, `webhook_deliveries`)
- Transactional outbox pattern for async dispatching.
- Fields (`outbox_events`): `id` (UUID), `event_id` (Index), `merchant_id` (FK), `event_type`, `processed` (Index).
