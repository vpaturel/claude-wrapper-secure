#!/usr/bin/env python3
"""
Test Long Context avec Claude OAuth via proxy
Objectif: Capturer performance avec 10-20K tokens input
"""

import subprocess
import time
import json
from datetime import datetime

# Long context prompt (~10K tokens estimé)
LONG_PROMPT = """
You are analyzing a complex software architecture. Below is a detailed description of a microservices system.

SYSTEM OVERVIEW:
The system consists of 15 microservices deployed on Kubernetes, handling e-commerce transactions.

SERVICE 1: User Authentication Service
- Tech stack: FastAPI, PostgreSQL, Redis
- Handles: Login, Registration, OAuth2, JWT tokens
- Database schema: users (id, email, password_hash, created_at, last_login, mfa_enabled)
- Redis caching: session tokens (1h TTL), refresh tokens (30d TTL)
- API endpoints:
  * POST /auth/register - Register new user
  * POST /auth/login - Login with credentials
  * POST /auth/refresh - Refresh access token
  * POST /auth/logout - Invalidate tokens
  * GET /auth/profile - Get user profile
- Performance: 500 req/sec, P95 latency 50ms
- Dependencies: PostgreSQL primary (read replica for GET), Redis cluster
- Security: bcrypt password hashing, rate limiting (10 req/min per IP)

SERVICE 2: Product Catalog Service
- Tech stack: Node.js Express, MongoDB, Elasticsearch
- Handles: Product listings, search, filtering, recommendations
- Database: products collection (100K+ documents)
- Schema: {id, name, description, price, category, tags[], images[], inventory_count, created_at}
- Elasticsearch index: full-text search on name/description, faceted filtering
- API endpoints:
  * GET /products - List products (pagination, filtering)
  * GET /products/:id - Get product details
  * POST /products/search - Full-text search
  * GET /products/recommendations - ML-based recommendations
- Performance: 1000 req/sec, P95 latency 30ms
- Caching: Redis for hot products (5min TTL)
- ML model: collaborative filtering deployed on SageMaker

SERVICE 3: Shopping Cart Service
- Tech stack: Go, Redis, PostgreSQL
- Handles: Add/remove items, cart persistence, price calculations
- Data model: carts table + cart_items table
- Redis: active carts cached (user_id → cart data), 24h TTL
- Business logic:
  * Inventory check before add
  * Price recalculation on quantity change
  * Coupon code validation
  * Stock reservation (15min hold)
- API endpoints:
  * GET /cart - Get current cart
  * POST /cart/items - Add item to cart
  * PUT /cart/items/:id - Update quantity
  * DELETE /cart/items/:id - Remove item
  * POST /cart/apply-coupon - Apply discount code
- Performance: 800 req/sec, P95 latency 40ms

SERVICE 4: Order Management Service
- Tech stack: Java Spring Boot, PostgreSQL, Kafka
- Handles: Order creation, status tracking, fulfillment workflow
- Database: orders, order_items, order_status_history tables
- Workflow states: PENDING → PAYMENT_PROCESSING → CONFIRMED → SHIPPED → DELIVERED
- Kafka topics:
  * order.created - Order created event
  * order.confirmed - Payment successful
  * order.shipped - Shipping notification
  * order.delivered - Delivery confirmation
- API endpoints:
  * POST /orders - Create new order
  * GET /orders/:id - Get order details
  * GET /orders/user/:user_id - List user orders
  * PUT /orders/:id/cancel - Cancel order
- Integration: Payment service, Inventory service, Shipping service
- Performance: 200 orders/sec, P95 latency 100ms
- Idempotency: order_id generation UUID v4, duplicate detection

SERVICE 5: Payment Processing Service
- Tech stack: Python FastAPI, PostgreSQL, Stripe SDK
- Handles: Payment intents, 3D Secure, refunds, webhooks
- PCI compliance: No card data stored, Stripe tokenization
- Payment methods: Credit card, PayPal, Apple Pay, Google Pay
- Workflow:
  1. Create payment intent
  2. Confirm with payment method
  3. Handle 3D Secure challenge
  4. Process authorization
  5. Capture funds
  6. Send confirmation
- API endpoints:
  * POST /payments/intent - Create payment intent
  * POST /payments/confirm - Confirm payment
  * POST /payments/refund - Refund transaction
  * POST /webhooks/stripe - Stripe webhook handler
- Error handling: Retry logic (exponential backoff), idempotency keys
- Performance: 300 payments/sec, P95 latency 200ms (Stripe API latency)

SERVICE 6: Inventory Management Service
- Tech stack: Rust, PostgreSQL, Redis
- Handles: Stock levels, reservations, restock notifications
- Real-time updates: WebSocket connection to frontend
- Database: inventory table (product_id, warehouse_id, quantity, reserved_quantity)
- Redis: stock levels cached, pub/sub for real-time updates
- Reservation logic:
  * Reserve stock on cart add (15min hold)
  * Release on cart abandon or order cancel
  * Decrement on order confirm
- Low stock alerts: When quantity < threshold, trigger restock workflow
- API endpoints:
  * GET /inventory/:product_id - Check stock
  * POST /inventory/reserve - Reserve stock
  * POST /inventory/release - Release reservation
  * PUT /inventory/:product_id - Update stock level
- Performance: 2000 req/sec, P95 latency 20ms (Redis reads)
- Concurrency: Optimistic locking with version field

SERVICE 7: Shipping Service
- Tech stack: Node.js, PostgreSQL, FedEx/UPS APIs
- Handles: Shipping rate calculation, label generation, tracking
- Integration: FedEx, UPS, USPS APIs
- Rate shopping: Query multiple carriers, return cheapest/fastest options
- API endpoints:
  * POST /shipping/rates - Get shipping rates
  * POST /shipping/labels - Generate shipping label
  * GET /shipping/track/:tracking_number - Track shipment
- Webhook: Carrier status updates → update order status
- Performance: 100 req/sec, P95 latency 500ms (carrier API latency)

SERVICE 8: Notification Service
- Tech stack: Python, SQS, SNS, SendGrid, Twilio
- Handles: Email, SMS, push notifications
- Channels: Email (transactional), SMS (OTP), Push (mobile app)
- Templates: Jinja2 templates for emails
- Queue: SQS for async processing, DLQ for failed deliveries
- Events:
  * order.confirmed → Order confirmation email
  * order.shipped → Shipping notification
  * payment.failed → Payment failure alert
  * inventory.low → Restock alert (admin)
- API endpoints:
  * POST /notifications/email - Send email
  * POST /notifications/sms - Send SMS
  * POST /notifications/push - Send push notification
- Rate limiting: 1000 emails/hour per user (SendGrid limits)
- Performance: 500 notifications/sec

SERVICE 9: Analytics Service
- Tech stack: Python, ClickHouse, Apache Spark
- Handles: Real-time analytics, dashboards, reports
- Data sources: Kafka topics (all events), application logs
- Metrics tracked:
  * Sales: Revenue, orders/day, average order value
  * Users: DAU, MAU, retention rate, churn rate
  * Products: Views, add-to-cart rate, purchase rate
  * Performance: API latencies, error rates, uptime
- Dashboards: Grafana for ops, custom React dashboard for business
- Batch jobs: Daily sales reports, weekly cohort analysis
- API endpoints:
  * GET /analytics/sales - Sales metrics
  * GET /analytics/users - User metrics
  * GET /analytics/products/:id - Product analytics
- Performance: Query latency P95 < 1s (ClickHouse columnar DB)

SERVICE 10: Search Service
- Tech stack: Python, Elasticsearch, Redis
- Handles: Product search, autocomplete, faceted navigation
- Index: 100K+ products, updated real-time via Kafka
- Features:
  * Full-text search (name, description, tags)
  * Faceted filtering (category, price range, brand, rating)
  * Autocomplete (prefix search)
  * Typo tolerance (fuzzy matching)
  * Relevance tuning (boosting fields, synonyms)
- Caching: Popular searches cached in Redis (1h TTL)
- API endpoints:
  * GET /search - Search products
  * GET /search/autocomplete - Autocomplete suggestions
  * GET /search/facets - Get available filters
- Performance: 1500 req/sec, P95 latency 50ms

INFRASTRUCTURE:
- Kubernetes: 3-node cluster (AWS EKS)
- Load balancer: AWS ALB with sticky sessions
- Service mesh: Istio for mTLS, traffic management, observability
- Monitoring: Prometheus + Grafana, custom metrics
- Logging: FluentD → Elasticsearch → Kibana
- Tracing: Jaeger for distributed tracing
- CI/CD: GitLab CI, ArgoCD for GitOps
- Secrets: AWS Secrets Manager
- Database backups: Daily automated backups, 30d retention
- Disaster recovery: Multi-AZ deployment, cross-region replication

QUESTION:
Based on this architecture, identify:
1. Top 3 performance bottlenecks
2. Top 3 security vulnerabilities
3. Top 3 scalability concerns
4. Recommended improvements for each

Provide detailed analysis with specific code/config examples.
"""

def run_long_context_test():
    """Lancer test long context via proxy"""

    print("🧪 Test Long Context via Proxy")
    print("=" * 60)
    print(f"📊 Prompt size: ~{len(LONG_PROMPT)} chars (~{len(LONG_PROMPT.split())} words)")
    print(f"⏱️  Start time: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Lancer via proxy
    start_time = time.time()

    try:
        result = subprocess.run(
            ["claude", "--print", "--model", "sonnet", LONG_PROMPT],
            env={
                "HTTP_PROXY": "http://localhost:8000",
                "HTTPS_PROXY": "http://localhost:8000",
                "PATH": "/opt/claude/versions/2.0.33:/usr/local/bin:/usr/bin:/bin"
            },
            capture_output=True,
            text=True,
            timeout=180
        )

        elapsed = time.time() - start_time

        print(f"⏱️  Total time: {elapsed:.2f}s")
        print(f"📊 Response size: {len(result.stdout)} chars")
        print()

        if result.returncode == 0:
            print("✅ Success!")
            print()
            print("📝 Response preview (first 500 chars):")
            print("-" * 60)
            print(result.stdout[:500])
            print("...")
            print("-" * 60)

            # Metrics
            words_per_sec = len(result.stdout.split()) / elapsed
            print()
            print("📈 Performance Metrics:")
            print(f"  - Throughput: {words_per_sec:.1f} words/sec")
            print(f"  - Latency: {elapsed:.2f}s")
            print(f"  - Input tokens (est): ~{len(LONG_PROMPT.split()) * 1.3:.0f}")
            print(f"  - Output tokens (est): ~{len(result.stdout.split()) * 1.3:.0f}")

        else:
            print("❌ Error!")
            print(f"Exit code: {result.returncode}")
            print(f"Stderr: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("⏱️  TIMEOUT après 180s")
    except Exception as e:
        print(f"❌ Exception: {e}")

    print()
    print("📁 Check captures:")
    print("  ls -lht captures/streaming/*.json | head -1")
    print()

if __name__ == "__main__":
    run_long_context_test()
