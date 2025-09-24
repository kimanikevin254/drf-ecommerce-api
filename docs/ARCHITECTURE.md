# System Architecture

## Overview

The system follows Django best practices with clear separation of concerns.

## Components

-   **Django API**: REST endpoints with DRF
-   **PostgreSQL**: Primary database
-   **Redis**: Task queue
-   **Celery**: Background task processing
-   **Africa's Talking**: SMS notifications

## Project Structure

```bash
drf_ecommerce_api/
├── accounts/          # User management & auth
├── catalog/           # Categories & products
├── orders/            # Order processing
│   ├── services/      # Business logic services
│   ├── tasks.py       # Celery tasks
│   └── tests/         # Test files
├── core/              # Shared utilities
└── k8s/              # Kubernetes manifests
```

## Authentication Flow

1. User clicks "Login with Google"
2. Redirected to Google OAuth
3. Google callback creates/updates user
4. JWT tokens issued for API access

## Order Processing Flow

1. Validate stock availability
2. Create order with items
3. Update product stock
4. Trigger SMS + email notifications (async)
5. Return order confirmation
