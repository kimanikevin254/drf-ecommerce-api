# API Documentation

## Authentication

All order-related endpoints require JWT authentication via Google OIDC (for customers).

### Get JWT Tokens

```http
GET /api/v1/auth/google/login/
```

## Categories

### List Categories

```http
GET /api/v1/catalog/categories/
```

### Create Category (Admin Only)

```http
POST GET /api/v1/catalog/categories/
Authorization: Bearer <token>

{
    "name": "Electronics",
    "parent": null
}
```

### Get Category Details

```http
GET /api/v1/catalog/categories/{id}/
```

### Update Category Details (Admin Only)

```http
PATCH /api/v1/catalog/categories/{id}/

{
    "name": "Updated Name"
}
```

### Delete Category

```http
DELETE /api/v1/catalog/categories/{id}/
```

### Get Category Average Price

```http
GET /api/v1/catalog/categories/{id}/average-price/
```

## Products

### List Products

```http
GET /api/v1/catalog/products/
GET /api/v1/catalog/products/?category=1&search=phone&ordering=price
```

### Create Product (Admin Only)

```http
POST /api/v1/catalog/products/
Authorization: Bearer <token>

{
  "name": "iPhone 15",
  "description": "Latest iPhone",
  "price": "999.99",
  "category": 1,
  "stock_quantity": 10
}
```

## Orders

### Create Order (Customer Only)

```http
POST /api/v1/orders/
Authorization: Bearer <token>

{
  "customer_phone": "+254700000000",
  "delivery_address": "123 Main St",
  "save_as_default": true,
  "items": [
    {
      "product": 1,
      "quantity": 2
    }
  ]
}
```

### List Orders

```http
GET /api/v1/orders/
Authorization: Bearer <token>
```

## Response Format

All API responses follow this structure:

```json
{
  "success": true,
  "errors": null,
  "data": { ... }
}
```

Error responses:

```json
{
    "success": false,
    "errors": { "field": ["Error message"] },
    "data": null
}
```
