# Testing Guide

## Running Tests

```bash
# All tests
python manage.py test --settings=ecommerce_api.settings_test

# Specific app
python manage.py test orders --settings=ecommerce_api.settings_test

# With coverage
coverage run manage.py test --settings=ecommerce_api.settings_test
coverage report
coverage html
```

## Test Structure

-   `orders/tests.py` - Order creation, permissions, business logic
-   `orders/test_tasks.py` - Celery task testing
-   `orders/test_services.py` - SMS/email service testing
-   `catalog/tests.py` - Category/product CRUD and permissions

## Coverage Target

Maintain >80% test coverage across all apps.

## CI/CD

Tests run automatically on `main` branch deployments.
