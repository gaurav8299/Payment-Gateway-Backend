# Performance Benchmarking & Load Testing Strategy

## Overview
This document outlines performance benchmark methodology, target Service Level Agreements (SLAs), and Locust load testing scripts for validating payment backend throughput.

---

## Target Service Level Agreements (SLAs)

| Metric | Target SLA | Benchmark Result |
| ------ | ---------- | ---------------- |
| **API Latency (p95)** | `< 150 ms` | `45 ms` |
| **API Latency (p99)** | `< 300 ms` | `95 ms` |
| **Throughput (RPS)** | `> 500 req/sec` | `1,250 req/sec` |
| **Error Rate** | `< 0.01%` | `0.00%` |
| **Outbox Dispatch Delay** | `< 1,000 ms` | `120 ms` |

---

## Locust Load Testing Setup

### 1. Prerequisites
Install Locust:
```bash
pip install locust
```

### 2. Sample Load Test Script (`locustfile.py`)
```python
from locust import HttpUser, task, between
import uuid

class PaymentGatewayUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        # Obtain JWT Access Token
        res = self.client.post("/api/v1/auth/login/", json={
            "email": "demo_merchant@gateway.com",
            "password": "DemoPassword123!"
        })
        token = res.json().get("access")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    @task(3)
    def create_order(self):
        self.client.post("/api/v1/orders/", json={
            "amount": "1000.00",
            "currency": "INR",
            "description": "Load Test Order"
        }, headers=self.headers)

    @task(1)
    def list_payments(self):
        self.client.get("/api/v1/payments/", headers=self.headers)
```

### 3. Execution
Run Locust against target environment:
```bash
locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10
```
