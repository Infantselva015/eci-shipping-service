# Shipping Service - ECI Microservices

## Overview
The Shipping Service is responsible for managing shipments, tracking, and delivery status updates for the E-commerce with Inventory (ECI) platform.

## Features
- ✅ Create shipments for confirmed orders
- ✅ Update shipment status and tracking information
- ✅ Track shipments by tracking number
- ✅ Cancel shipments (with business rules)
- ✅ Event-driven tracking history
- ✅ Multiple carrier support (DHL, FedEx, BlueDart, DTDC)
- ✅ RESTful API with OpenAPI 3.0 documentation
- ✅ Database-per-service pattern (Shipping DB)
- ✅ Health checks and metrics endpoints
- ✅ Docker containerization
- ✅ Kubernetes deployment manifests

## Technology Stack
- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **API Documentation**: OpenAPI 3.0 (Swagger UI)
- **Containerization**: Docker
- **Orchestration**: Kubernetes (Minikube)

## Database Schema

### Tables
1. **shipments**: Main shipment records
   - shipment_id (PK)
   - order_id (UNIQUE, FK to Order Service)
   - carrier (DHL, FedEx, BlueDart, DTDC)
   - status (PENDING, PACKED, SHIPPED, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, FAILED, CANCELLED)
   - tracking_no (UNIQUE)
   - shipped_at, delivered_at
   - created_at, updated_at

2. **shipment_events**: Tracking history
   - event_id (PK)
   - shipment_id (FK)
   - status, location, description
   - created_at

## API Endpoints

### Base URL: `/v1`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/shipments` | Create a new shipment |
| GET | `/v1/shipments/{shipment_id}` | Get shipment by ID |
| GET | `/v1/shipments/order/{order_id}` | Get shipment by order ID |
| GET | `/v1/shipments/tracking/{tracking_no}` | Track shipment by tracking number |
| PATCH | `/v1/shipments/{shipment_id}/status` | Update shipment status |
| DELETE | `/v1/shipments/{shipment_id}` | Cancel shipment |
| GET | `/v1/shipments` | List shipments (with filters & pagination) |
| GET | `/health` | Health check |
| GET | `/metrics` | Service metrics |

## Sample Requests

### 1. Create Shipment
```bash
curl -X POST http://localhost:8085/v1/shipments \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1001,
    "carrier": "DHL",
    "shipping_address": {
      "street": "123 Main St",
      "city": "New York",
      "state": "NY",
      "zip": "10001"
    }
  }'
```

### 2. Update Shipment Status
```bash
curl -X PATCH http://localhost:8085/v1/shipments/1/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "SHIPPED",
    "location": "New York Distribution Center",
    "description": "Package picked up and in transit"
  }'
```

### 3. Track Shipment
```bash
curl http://localhost:8085/v1/shipments/tracking/TRK1234
```

### 4. List Shipments with Filters
```bash
curl "http://localhost:8085/v1/shipments?status=SHIPPED&carrier=DHL&skip=0&limit=10"
```

## Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Docker & Docker Compose
- Minikube (for Kubernetes deployment)

### Setup & Run

1. **Clone the repository**
```bash
git clone <repository-url>
cd eci-microservices
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up database**
```bash
# Using Docker
docker run -d \
  --name shipping-postgres \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=shipping_db \
  -p 5432:5432 \
  postgres:14

# Initialize schema
psql -U user -d shipping_db -f db/init.sql
```

4. **Run the service**
```bash
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

5. **Access API documentation**
- Swagger UI: http://localhost:8085/docs
- ReDoc: http://localhost:8085/redoc

## Docker Deployment

### Build Image
```bash
docker build -t shipping-service:latest .
```

### Run with Docker Compose
```bash
docker-compose up -d
```

### Test Container
```bash
docker ps
curl http://localhost:8085/health
```

## Kubernetes Deployment

### Prerequisites
```bash
# Start Minikube
minikube start

# Enable required addons
minikube addons enable metrics-server
minikube addons enable ingress
```

### Deploy to Minikube

1. **Build image in Minikube**
```bash
eval $(minikube docker-env)
docker build -t shipping-service:latest .
```

2. **Apply Kubernetes manifests**
```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

3. **Verify deployment**
```bash
kubectl get pods
kubectl get services
kubectl logs -f deployment/shipping-service
```

4. **Access the service**
```bash
minikube service shipping-service --url
```

## Monitoring & Observability

### Health Checks
```bash
# Health endpoint
curl http://localhost:8085/health

# Kubernetes liveness probe
kubectl describe pod <pod-name>
```

### Metrics
```bash
# Service metrics
curl http://localhost:8085/metrics
```

### Logs
```bash
# Docker logs
docker logs shipping-service

# Kubernetes logs
kubectl logs -f deployment/shipping-service

# Structured JSON logs (production)
# All logs include: timestamp, level, service, message, context
```

## Business Logic & Rules

### Shipment Lifecycle
1. **PENDING** → Order confirmed, awaiting packing
2. **PACKED** → Items packed, ready for pickup
3. **SHIPPED** → Picked up by carrier, shipped_at timestamp set
4. **IN_TRANSIT** → Package in transit
5. **OUT_FOR_DELIVERY** → Out for final delivery
6. **DELIVERED** → Successfully delivered, delivered_at timestamp set
7. **FAILED** → Delivery failed, requires attention
8. **CANCELLED** → Shipment cancelled

### Cancellation Rules
- ✅ Can cancel: PENDING, PACKED, SHIPPED
- ❌ Cannot cancel: DELIVERED, CANCELLED
- When cancelled:
  - Status updated to CANCELLED
  - Event logged in shipment_events
  - Inventory Service should be notified to RELEASE/RESTOCK

### Tracking Events
- Every status change creates a tracking event
- Events include: timestamp, status, location, description
- Full audit trail for customer service

## Inter-Service Communication

### Integration with Order Service
- **Trigger**: Order Service calls POST `/v1/shipments` when order is CONFIRMED and PAID
- **Data**: Receives order_id, carrier preference, shipping address
- **Response**: Returns shipment_id, tracking_no

### Integration with Inventory Service
- **On Cancellation**: Notify Inventory to RELEASE reserved quantities
- **On Status Update**: Can trigger inventory movements (SHIP operation)

### Integration with Notification Service
- **Events to Notify**:
  - Shipment created → Send tracking number to customer
  - Shipped → "Your order has been shipped"
  - Out for delivery → "Arriving today"
  - Delivered → "Order delivered successfully"

## Error Handling

### Standard Error Response
```json
{
  "detail": "Error message",
  "status_code": 400,
  "timestamp": "2025-10-31T10:30:00Z"
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `409` - Conflict (duplicate shipment)
- `500` - Internal Server Error

## Testing

### Manual Testing with Sample Requests
```bash
# Use provided sample JSON files
curl -X POST http://localhost:8085/v1/shipments \
  -H "Content-Type: application/json" \
  -d @sample_requests/create_shipment.json

curl -X PATCH http://localhost:8085/v1/shipments/1/status \
  -H "Content-Type: application/json" \
  -d @sample_requests/update_status.json
```

### Health Check Testing
```bash
# Local
curl http://localhost:8085/health

# Kubernetes
kubectl exec -it <pod-name> -- curl http://localhost:8085/health
```

## Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `PORT`: Service port (default: 8005)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, ERROR)

### ConfigMap (Kubernetes)
See `k8s/configmap.yaml` for configuration values

## Architecture Decisions

### Database-Per-Service Pattern
- ✅ Shipping DB owns shipments and shipment_events tables
- ✅ No direct database access from other services
- ✅ Communication via REST APIs only
- ✅ order_id stored as reference (not FK to other service DB)

### Read Model
- Shipment stores order_id for reference
- Does NOT duplicate order details (maintained by Order Service)
- Minimal coupling between services

## Future Enhancements
- [ ] Idempotency keys for create shipment
- [ ] Webhook integration with real carrier APIs
- [ ] Real-time tracking updates
- [ ] Multi-warehouse shipment splitting
- [ ] Estimated delivery date calculation
- [ ] Prometheus metrics export
- [ ] Grafana dashboards
- [ ] Rate limiting
- [ ] Circuit breakers for external carrier APIs

## Contributing
This service is part of the ECI Microservices project for BITS WILP Scalable Services course.

## License
MIT

