# Shipping Service - ECI Microservices



## Overview

The Shipping Service manages shipment creation, tracking, and delivery status updates for e-commerce orders. It provides comprehensive shipment lifecycle management with multi-carrier support and real-time tracking capabilities.The Shipping Service is responsible for managing shipments, tracking, and delivery status updates for the E-commerce with Inventory (ECI) platform.



# Features

- **Shipment Management**: Create, update, and cancel shipments- ✅ Create shipments for confirmed orders

- **Multi-Carrier Support**: DHL, FedEx, BlueDart, DTDC- ✅ Update shipment status and tracking information

- **Real-time Tracking**: Track shipments by tracking number with event history- ✅ Track shipments by tracking number

- **Idempotent Operations**: Prevents duplicate shipments using idempotency keys- ✅ Cancel shipments (with business rules)

- **Status Lifecycle**: Complete shipment status tracking from pending to delivery- ✅ Event-driven tracking history

- **RESTful API**: OpenAPI 3.0 compliant with Swagger documentation- ✅ Multiple carrier support (DHL, FedEx, BlueDart, DTDC)

- **Observability**: Prometheus metrics, structured logging with PII masking- ✅ RESTful API with OpenAPI 3.0 documentation

- **Inter-service Integration**: Automated coordination with Inventory and Notification services- ✅ Database-per-service pattern (Shipping DB)

- ✅ Health checks and metrics endpoints

## Technology Stack- ✅ Docker containerization

- **Language**: Python 3.11- ✅ Kubernetes deployment manifests

- **Framework**: FastAPI 0.104.1

- **Database**: PostgreSQL 14## Technology Stack

- **ORM**: SQLAlchemy 2.0.23- **Framework**: FastAPI (Python 3.11)

- **Monitoring**: Prometheus Client- **Database**: PostgreSQL

- **Containerization**: Docker- **ORM**: SQLAlchemy

- **Orchestration**: Kubernetes- **API Documentation**: OpenAPI 3.0 (Swagger UI)

- **Containerization**: Docker

## Architecture- **Orchestration**: Kubernetes (Minikube)



### Database Schema## Database Schema



The service uses a dedicated PostgreSQL database (`shipping_db`) with three tables:### Tables

1. **shipments**: Main shipment records

**1. shipments** - Main shipment records   - shipment_id (PK)

```sql   - order_id (UNIQUE, FK to Order Service)

- shipment_id (Primary Key)   - carrier (DHL, FedEx, BlueDart, DTDC)

- order_id (Unique, indexed)   - status (PENDING, PACKED, SHIPPED, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, FAILED, CANCELLED)

- carrier (DHL, FedEx, BlueDart, DTDC)   - tracking_no (UNIQUE)

- status (PENDING, PACKED, SHIPPED, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, FAILED, CANCELLED)   - shipped_at, delivered_at

- tracking_no (Unique)   - created_at, updated_at

- shipped_at, delivered_at (timestamps)

- created_at, updated_at2. **shipment_events**: Tracking history

```   - event_id (PK)

   - shipment_id (FK)

**2. shipment_events** - Tracking history and audit trail   - status, location, description

```sql   - created_at

- event_id (Primary Key)

- shipment_id (Foreign Key)## API Endpoints

- status, location, description

- created_at### Base URL: `/v1`

```

| Method | Endpoint | Description |

**3. idempotency_keys** - Prevents duplicate operations|--------|----------|-------------|

```sql| POST | `/v1/shipments` | Create a new shipment |

- id (Primary Key)| GET | `/v1/shipments/{shipment_id}` | Get shipment by ID |

- key (Unique)| GET | `/v1/shipments/order/{order_id}` | Get shipment by order ID |

- request_hash (SHA-256)| GET | `/v1/shipments/tracking/{tracking_no}` | Track shipment by tracking number |

- response_data (Cached response)| PATCH | `/v1/shipments/{shipment_id}/status` | Update shipment status |

- expires_at (24-hour TTL)| DELETE | `/v1/shipments/{shipment_id}` | Cancel shipment |

```| GET | `/v1/shipments` | List shipments (with filters & pagination) |

| GET | `/health` | Health check |

### Shipment Status Lifecycle| GET | `/metrics` | Service metrics |

```

PENDING → PACKED → SHIPPED → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED## Sample Requests

                      ↓

                  FAILED / CANCELLED### 1. Create Shipment

``````bash

curl -X POST http://localhost:8085/v1/shipments \

## API Endpoints  -H "Content-Type: application/json" \

  -d '{

**Base URL**: `/v1`    "order_id": 1001,

    "carrier": "DHL",

| Method | Endpoint | Description | Idempotent |    "shipping_address": {

|--------|----------|-------------|------------|      "street": "123 Main St",

| POST | `/v1/shipments` | Create new shipment | Yes |      "city": "New York",

| GET | `/v1/shipments/{shipment_id}` | Get shipment by ID | - |      "state": "NY",

| GET | `/v1/shipments/order/{order_id}` | Get shipment by order | - |      "zip": "10001"

| GET | `/v1/shipments/tracking/{tracking_no}` | Track shipment | - |    }

| PATCH | `/v1/shipments/{shipment_id}/status` | Update status | No |  }'

| DELETE | `/v1/shipments/{shipment_id}` | Cancel shipment | No |```

| GET | `/v1/shipments` | List with filters | - |

| GET | `/health` | Health check | - |### 2. Update Shipment Status

| GET | `/metrics` | Prometheus metrics | - |```bash

| GET | `/metrics/summary` | Metrics dashboard | - |curl -X PATCH http://localhost:8085/v1/shipments/1/status \

  -H "Content-Type: application/json" \

## Quick Start  -d '{

    "status": "SHIPPED",

### Using Docker Compose    "location": "New York Distribution Center",

    "description": "Package picked up and in transit"

1. **Start the service**  }'

```bash```

docker-compose up -d

```### 3. Track Shipment

```bash

2. **Verify health**curl http://localhost:8085/v1/shipments/tracking/TRK1234

```bash```

curl http://localhost:8085/health

```### 4. List Shipments with Filters

```bash

3. **Access API documentation**curl "http://localhost:8085/v1/shipments?status=SHIPPED&carrier=DHL&skip=0&limit=10"

``````

Swagger UI: http://localhost:8085/docs

```## Local Development



### Using Kubernetes (Minikube)### Prerequisites

- Python 3.11+

1. **Build and deploy**- PostgreSQL 14+

```bash- Docker & Docker Compose

eval $(minikube docker-env)- Minikube (for Kubernetes deployment)

docker build -t shipping-service:latest .

kubectl apply -f k8s/### Setup & Run

```

1. **Clone the repository**

2. **Get service URL**```bash

```bashgit clone <repository-url>

minikube service shipping-service --urlcd eci-microservices

``````



## API Usage Examples2. **Install dependencies**

```bash

### Create Shipment (Idempotent)pip install -r requirements.txt

```bash```

curl -X POST http://localhost:8085/v1/shipments \

  -H "Content-Type: application/json" \3. **Set up database**

  -H "Idempotency-Key: unique-key-123" \```bash

  -d '{# Using Docker

    "order_id": 101,docker run -d \

    "carrier": "DHL",  --name shipping-postgres \

    "shipping_address": {  -e POSTGRES_USER=user \

      "street": "221B Baker Street",  -e POSTGRES_PASSWORD=password \

      "city": "London",  -e POSTGRES_DB=shipping_db \

      "postal_code": "NW1 6XE",  -p 5432:5432 \

      "country": "UK"  postgres:14

    }

  }'# Initialize schema

```psql -U user -d shipping_db -f db/init.sql

```

**Response:**

```json4. **Run the service**

{```bash

  "shipment_id": 1,uvicorn main:app --host 0.0.0.0 --port 8005 --reload

  "order_id": 101,```

  "carrier": "DHL",

  "status": "PENDING",5. **Access API documentation**

  "tracking_no": "TRK456789",- Swagger UI: http://localhost:8085/docs

  "created_at": "2025-11-03T10:30:00Z"- ReDoc: http://localhost:8085/redoc

}

```## Docker Deployment



### Track Shipment### Build Image

```bash```bash

curl http://localhost:8085/v1/shipments/tracking/TRK456789docker build -t shipping-service:latest .

``````



**Response:**### Run with Docker Compose

```json```bash

{docker-compose up -d

  "shipment": {```

    "shipment_id": 1,

    "order_id": 101,### Test Container

    "carrier": "DHL",```bash

    "status": "IN_TRANSIT",docker ps

    "tracking_no": "TRK456789",curl http://localhost:8085/health

    "shipped_at": "2025-11-03T11:00:00Z",```

    "delivered_at": null,

    "created_at": "2025-11-03T10:30:00Z",## Kubernetes Deployment

    "updated_at": "2025-11-03T12:00:00Z"

  },### Prerequisites

  "events": [```bash

    {# Start Minikube

      "event_id": 1,minikube start

      "status": "PENDING",

      "description": "Shipment created",# Enable required addons

      "created_at": "2025-11-03T10:30:00Z"minikube addons enable metrics-server

    },minikube addons enable ingress

    {```

      "event_id": 2,

      "status": "SHIPPED",### Deploy to Minikube

      "location": "London Distribution Center",

      "description": "Package picked up by carrier",1. **Build image in Minikube**

      "created_at": "2025-11-03T11:00:00Z"```bash

    }eval $(minikube docker-env)

  ]docker build -t shipping-service:latest .

}```

```

2. **Apply Kubernetes manifests**

### Update Status```bash

```bashkubectl apply -f k8s/configmap.yaml

curl -X PATCH http://localhost:8085/v1/shipments/1/status \kubectl apply -f k8s/deployment.yaml

  -H "Content-Type: application/json" \kubectl apply -f k8s/service.yaml

  -d '{```

    "status": "DELIVERED",

    "location": "Customer Address",3. **Verify deployment**

    "description": "Package delivered successfully"```bash

  }'kubectl get pods

```kubectl get services

kubectl logs -f deployment/shipping-service

### Cancel Shipment```

```bash

curl -X DELETE http://localhost:8085/v1/shipments/14. **Access the service**

``````bash

minikube service shipping-service --url

### List Shipments with Filters```

```bash

curl "http://localhost:8085/v1/shipments?status=SHIPPED&carrier=DHL&skip=0&limit=10"## Monitoring & Observability

```

### Health Checks

## Business Rules```bash

# Health endpoint

### Shipment Creationcurl http://localhost:8085/health

- Requires confirmed and paid order from Order Service

- Automatically generates unique tracking number# Kubernetes liveness probe

- Creates initial "PENDING" event in tracking historykubectl describe pod <pod-name>

- Supports idempotency to prevent duplicate shipments```



### Status Updates### Metrics

- Status transitions follow defined lifecycle```bash

- Each update creates a tracking event# Service metrics

- Timestamps (shipped_at, delivered_at) auto-set based on statuscurl http://localhost:8085/metrics

- Location and description optional for context```



### Cancellation### Logs

- **Allowed**: PENDING, PACKED, SHIPPED, IN_TRANSIT```bash

- **Not Allowed**: DELIVERED, CANCELLED# Docker logs

- Automatically notifies Inventory Service to release reserved stockdocker logs shipping-service

- Creates cancellation event in tracking history

# Kubernetes logs

## Inter-Service Communicationkubectl logs -f deployment/shipping-service



### Order Service Integration# Structured JSON logs (production)

- Receives shipment creation requests after order confirmation# All logs include: timestamp, level, service, message, context

- Returns tracking number for order updates```



### Inventory Service Integration## Business Logic & Rules

- Sends release notification when shipment is cancelled

- Endpoint: `POST {INVENTORY_SERVICE_URL}/v1/inventory/release`### Shipment Lifecycle

- Async HTTP call with timeout protection1. **PENDING** → Order confirmed, awaiting packing

2. **PACKED** → Items packed, ready for pickup

### Notification Service Integration3. **SHIPPED** → Picked up by carrier, shipped_at timestamp set

- Triggers notifications for key status changes:4. **IN_TRANSIT** → Package in transit

  - Shipment created → Send tracking number5. **OUT_FOR_DELIVERY** → Out for final delivery

  - Shipped → "Order shipped" notification6. **DELIVERED** → Successfully delivered, delivered_at timestamp set

  - Out for delivery → "Arriving today" notification7. **FAILED** → Delivery failed, requires attention

  - Delivered → "Successfully delivered" notification8. **CANCELLED** → Shipment cancelled



## Monitoring & Observability### Cancellation Rules

- ✅ Can cancel: PENDING, PACKED, SHIPPED

### Prometheus Metrics- ❌ Cannot cancel: DELIVERED, CANCELLED

Available at `/metrics` endpoint:- When cancelled:

```  - Status updated to CANCELLED

- shipments_created_total  - Event logged in shipment_events

- shipments_delivered_total  - Inventory Service should be notified to RELEASE/RESTOCK

- shipments_cancelled_total

- shipments_failed_total### Tracking Events

- status_updates_total- Every status change creates a tracking event

- api_requests_total{method, endpoint, status}- Events include: timestamp, status, location, description

- shipment_operation_latency_seconds{operation}- Full audit trail for customer service

```

## Inter-Service Communication

### Metrics Dashboard

Human-readable metrics at `/metrics/summary`:### Integration with Order Service

```json- **Trigger**: Order Service calls POST `/v1/shipments` when order is CONFIRMED and PAID

{- **Data**: Receives order_id, carrier preference, shipping address

  "service": "shipping-service",- **Response**: Returns shipment_id, tracking_no

  "timestamp": "2025-11-03T12:00:00Z",

  "status": "operational",### Integration with Inventory Service

  "database_metrics": {- **On Cancellation**: Notify Inventory to RELEASE reserved quantities

    "total_shipments": 150,- **On Status Update**: Can trigger inventory movements (SHIP operation)

    "pending_shipments": 10,

    "in_transit_shipments": 20,### Integration with Notification Service

    "delivered_shipments": 120,- **Events to Notify**:

    "failed_shipments": 0  - Shipment created → Send tracking number to customer

  }  - Shipped → "Your order has been shipped"

}  - Out for delivery → "Arriving today"

```  - Delivered → "Order delivered successfully"



### Structured Logging## Error Handling

- JSON-formatted logs with timestamp, level, service, message

- **PII Masking**: Automatically masks sensitive data### Standard Error Response

  - Emails: `user@example.com` → `***@***.***````json

  - Phone numbers: `123-456-7890` → `***-***-****`{

  - Tracking numbers: `TRK123456` → `TRK123***`  "detail": "Error message",

  "status_code": 400,

## Configuration  "timestamp": "2025-10-31T10:30:00Z"

}

### Environment Variables```

```bash

DATABASE_URL=postgresql://user:password@shipping-db:5432/shipping_db### HTTP Status Codes

INVENTORY_SERVICE_URL=http://inventory-service:8003- `200` - Success

ORDER_SERVICE_URL=http://order-service:8002- `201` - Created

RESERVATION_TTL_MINUTES=15- `400` - Bad Request

LOG_LEVEL=INFO- `404` - Not Found

```- `409` - Conflict (duplicate shipment)

- `500` - Internal Server Error

### Docker Compose

```bash## Testing

# Start services

docker-compose up -d### Manual Testing with Sample Requests

```bash

# View logs# Use provided sample JSON files

docker-compose logs -f shipping-servicecurl -X POST http://localhost:8085/v1/shipments \

  -H "Content-Type: application/json" \

# Stop services  -d @sample_requests/create_shipment.json

docker-compose down

```curl -X PATCH http://localhost:8085/v1/shipments/1/status \

  -H "Content-Type: application/json" \

### Kubernetes  -d @sample_requests/update_status.json

```bash```

# Apply manifests

kubectl apply -f k8s/db-configmap.yaml### Health Check Testing

kubectl apply -f k8s/secret.yaml```bash

kubectl apply -f k8s/pvc.yaml# Local

kubectl apply -f k8s/configmap.yamlcurl http://localhost:8085/health

kubectl apply -f k8s/deployment.yaml

kubectl apply -f k8s/service.yaml# Kubernetes

kubectl exec -it <pod-name> -- curl http://localhost:8085/health

# Check status```

kubectl get pods

kubectl get services## Configuration



# View logs### Environment Variables

kubectl logs -f deployment/shipping-service- `DATABASE_URL`: PostgreSQL connection string

- `PORT`: Service port (default: 8005)

# Access service- `LOG_LEVEL`: Logging level (INFO, DEBUG, ERROR)

minikube service shipping-service --url

```### ConfigMap (Kubernetes)

See `k8s/configmap.yaml` for configuration values

## Error Handling

## Architecture Decisions

All errors follow a standard schema:

```json### Database-Per-Service Pattern

{- ✅ Shipping DB owns shipments and shipment_events tables

  "error": "Conflict",- ✅ No direct database access from other services

  "message": "Shipment already exists for order 101",- ✅ Communication via REST APIs only

  "status_code": 409,- ✅ order_id stored as reference (not FK to other service DB)

  "timestamp": "2025-11-03T12:00:00Z"

}### Read Model

```- Shipment stores order_id for reference

- Does NOT duplicate order details (maintained by Order Service)

**HTTP Status Codes:**- Minimal coupling between services

- `200` - Success

- `201` - Created## Future Enhancements

- `400` - Bad Request- [ ] Idempotency keys for create shipment

- `404` - Not Found- [ ] Webhook integration with real carrier APIs

- `409` - Conflict (duplicate shipment, invalid state)- [ ] Real-time tracking updates

- `500` - Internal Server Error- [ ] Multi-warehouse shipment splitting

- [ ] Estimated delivery date calculation

## Development- [ ] Prometheus metrics export

- [ ] Grafana dashboards

### Local Setup- [ ] Rate limiting

```bash- [ ] Circuit breakers for external carrier APIs

# Install dependencies

pip install -r requirements.txt## Contributing

This service is part of the ECI Microservices project for BITS WILP Scalable Services course.

# Run database

docker run -d \## License

  --name shipping-postgres \MIT

  -e POSTGRES_USER=user \

  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=shipping_db \
  -p 5432:5432 \
  postgres:14

# Initialize schema
psql -U user -d shipping_db -f db/init.sql

# Run service
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

### Testing
```bash
# Health check
curl http://localhost:8085/health

# Create shipment
curl -X POST http://localhost:8085/v1/shipments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-key-001" \
  -d @sample_requests/create_shipment.json

# Test idempotency (retry with same key)
curl -X POST http://localhost:8085/v1/shipments \
  -H "Idempotency-Key: test-key-001" \
  -d @sample_requests/create_shipment.json
# Should return same shipment_id

# View metrics
curl http://localhost:8085/metrics/summary
```

## Project Structure
```
eci-shipping-service/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container image
├── docker-compose.yml     # Local deployment
├── README.md              # This file
├── db/
│   ├── init.sql           # Database schema
│   └── init_with_seed.sql # Schema with seed data
├── k8s/
│   ├── configmap.yaml     # Environment config
│   ├── db-configmap.yaml  # DB initialization
│   ├── deployment.yaml    # K8s deployments
│   ├── service.yaml       # K8s services
│   ├── pvc.yaml          # Persistent volumes
│   └── secret.yaml        # Credentials
└── sample_requests/
    ├── create_shipment.json
    ├── update_status.json
    ├── track_shipment.json
    └── cancel_shipment.json
```

## License
MIT
