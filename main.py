from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging
import json
import os
import re
import hashlib
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Configure structured logging with PII masking
class PIIMaskingFormatter(logging.Formatter):
    """Custom formatter to mask PII in logs"""
    
    @staticmethod
    def mask_pii(text: str) -> str:
        # Mask email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***', text)
        # Mask phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '***-***-****', text)
        # Mask tracking numbers (keep first 3 chars)
        text = re.sub(r'\bTRK\d{4,}\b', lambda m: m.group(0)[:6] + '***', text)
        return text
    
    def format(self, record):
        original = super().format(record)
        return self.mask_pii(original)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
for handler in logger.handlers:
    handler.setFormatter(PIIMaskingFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Prometheus metrics
SHIPMENTS_CREATED = Counter('shipments_created_total', 'Total shipments created')
SHIPMENTS_DELIVERED = Counter('shipments_delivered_total', 'Total shipments delivered')
SHIPMENTS_CANCELLED = Counter('shipments_cancelled_total', 'Total shipments cancelled')
SHIPMENTS_FAILED = Counter('shipments_failed_total', 'Total shipments failed')
STATUS_UPDATES = Counter('status_updates_total', 'Total status updates')
API_REQUESTS = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
SHIPMENT_LATENCY = Histogram('shipment_operation_latency_seconds', 'Shipment operation latency', ['operation'])

app = FastAPI(
    title="Shipping Service API",
    description="Manages shipments, tracking, and delivery status for ECI E-commerce Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/shipping_db")
RESERVATION_TTL_MINUTES = int(os.getenv("RESERVATION_TTL_MINUTES", "15"))
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:8003")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order-service:8002")

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Enums
class ShipmentStatus(str, Enum):
    PENDING = "PENDING"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class Carrier(str, Enum):
    DHL = "DHL"
    BLUEDART = "Bluedart"
    FEDEX = "FedEx"
    DTDC = "DTDC"

# Models
class Shipment(Base):
    __tablename__ = "shipments"
    shipment_id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False, unique=True, index=True)
    carrier = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    tracking_no = Column(String(50), unique=True, nullable=False)
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ShipmentEvent(Base):
    __tablename__ = "shipment_events"
    event_id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, nullable=False, index=True)
    status = Column(String(50), nullable=False)
    location = Column(String(200), nullable=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    request_hash = Column(String(64), nullable=False)
    response_data = Column(String(2000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index('idx_idempotency_key', 'key'),
        Index('idx_expires_at', 'expires_at'),
    )

# Pydantic schemas
class ErrorResponse(BaseModel):
    """Standard error response schema"""
    error: str
    message: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

class CreateShipmentRequest(BaseModel):
    order_id: int
    carrier: Carrier = Field(default=Carrier.DHL)
    shipping_address: Optional[dict] = None
    
    @validator('order_id')
    def validate_order_id(cls, v):
        if v <= 0:
            raise ValueError('order_id must be positive')
        return v

class CreateShipmentResponse(BaseModel):
    shipment_id: int
    order_id: int
    carrier: str
    status: str
    tracking_no: str
    created_at: datetime

class UpdateStatusRequest(BaseModel):
    status: ShipmentStatus
    location: Optional[str] = None
    description: Optional[str] = None

class ShipmentResponse(BaseModel):
    shipment_id: int
    order_id: int
    carrier: str
    status: str
    tracking_no: str
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class TrackingEvent(BaseModel):
    event_id: int
    status: str
    location: Optional[str]
    description: Optional[str]
    created_at: datetime

class TrackingResponse(BaseModel):
    shipment: ShipmentResponse
    events: List[TrackingEvent]

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions
def generate_tracking_number(db: Session):
    """Generate unique tracking number"""
    import random
    while True:
        tracking_no = f"TRK{random.randint(100000, 999999)}"
        existing = db.query(Shipment).filter(Shipment.tracking_no == tracking_no).first()
        if not existing:
            return tracking_no

def select_carrier() -> str:
    """Select carrier based on availability (can be enhanced with logic)"""
    import random
    return random.choice([c.value for c in Carrier])

def compute_request_hash(data: dict) -> str:
    """Compute SHA-256 hash of request data"""
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()

def check_idempotency(db: Session, idempotency_key: str, request_data: dict) -> Optional[dict]:
    """Check if request has been processed before"""
    if not idempotency_key:
        return None
    
    # Clean up expired keys
    db.query(IdempotencyKey).filter(IdempotencyKey.expires_at < datetime.utcnow()).delete()
    db.commit()
    
    existing = db.query(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key).first()
    if existing:
        request_hash = compute_request_hash(request_data)
        if existing.request_hash == request_hash:
            # Return cached response
            return json.loads(existing.response_data)
        else:
            # Same key, different request - error
            raise HTTPException(
                status_code=409,
                detail="Idempotency key already used with different request data"
            )
    return None

def store_idempotency(db: Session, idempotency_key: str, request_data: dict, response_data: dict):
    """Store idempotency key and response"""
    if not idempotency_key:
        return
    
    request_hash = compute_request_hash(request_data)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    idempotency_record = IdempotencyKey(
        key=idempotency_key,
        request_hash=request_hash,
        response_data=json.dumps(response_data, default=str),
        expires_at=expires_at
    )
    db.add(idempotency_record)
    db.commit()

async def notify_inventory_release(order_id: int, reason: str):
    """Notify Inventory Service to release reserved stock"""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{INVENTORY_SERVICE_URL}/v1/inventory/release",
                json={"order_id": order_id, "reason": reason},
                timeout=5.0
            )
            if response.status_code == 200:
                logger.info(f"Successfully notified inventory to release for order {order_id}")
            else:
                logger.warning(f"Failed to notify inventory release: {response.status_code}")
    except Exception as e:
        logger.error(f"Error notifying inventory service: {str(e)}")

# Custom exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail if isinstance(exc.detail, str) else "HTTP Exception",
            message=str(exc.detail),
            status_code=exc.status_code,
            timestamp=datetime.utcnow()
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            message="An unexpected error occurred",
            status_code=500,
            timestamp=datetime.utcnow()
        ).dict()
    )

# API Endpoints

@app.post("/v1/shipments", response_model=CreateShipmentResponse, status_code=201)
async def create_shipment(
    request: CreateShipmentRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db)
):
    """
    Create a new shipment for an order (Idempotent)
    
    Headers:
    - Idempotency-Key: Unique key to prevent duplicate shipment creation
    """
    with SHIPMENT_LATENCY.labels(operation='create').time():
        try:
            # Check idempotency
            request_data = request.dict()
            cached_response = check_idempotency(db, idempotency_key, request_data)
            if cached_response:
                logger.info(f"Returning cached response for idempotency key: {idempotency_key}")
                API_REQUESTS.labels(method='POST', endpoint='/v1/shipments', status='200').inc()
                return JSONResponse(content=cached_response, status_code=201)
            
            # Check if shipment already exists for order
            existing = db.query(Shipment).filter(Shipment.order_id == request.order_id).first()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Shipment already exists for order {request.order_id}"
                )
            
            # Create shipment
            shipment = Shipment(
                order_id=request.order_id,
                carrier=request.carrier.value,
                status=ShipmentStatus.PENDING.value,
                tracking_no=generate_tracking_number(db)
            )
            db.add(shipment)
            db.flush()
            
            # Create initial event
            event = ShipmentEvent(
                shipment_id=shipment.shipment_id,
                status=ShipmentStatus.PENDING.value,
                description="Shipment created"
            )
            db.add(event)
            
            db.commit()
            db.refresh(shipment)
            
            # Update metrics
            SHIPMENTS_CREATED.inc()
            API_REQUESTS.labels(method='POST', endpoint='/v1/shipments', status='201').inc()
            
            response_data = {
                "shipment_id": shipment.shipment_id,
                "order_id": shipment.order_id,
                "carrier": shipment.carrier,
                "status": shipment.status,
                "tracking_no": shipment.tracking_no,
                "created_at": shipment.created_at.isoformat()
            }
            
            # Store idempotency
            store_idempotency(db, idempotency_key, request_data, response_data)
            
            logger.info(json.dumps({
                "event": "shipment_created",
                "shipment_id": shipment.shipment_id,
                "order_id": request.order_id,
                "carrier": shipment.carrier,
                "tracking_no": shipment.tracking_no
            }))
            
            return CreateShipmentResponse(**response_data)
            
        except HTTPException:
            API_REQUESTS.labels(method='POST', endpoint='/v1/shipments', status='error').inc()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create shipment: {str(e)}")
            API_REQUESTS.labels(method='POST', endpoint='/v1/shipments', status='500').inc()
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/shipments/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(shipment_id: int, db: Session = Depends(get_db)):
    """Get shipment details"""
    shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    return ShipmentResponse(
        shipment_id=shipment.shipment_id,
        order_id=shipment.order_id,
        carrier=shipment.carrier,
        status=shipment.status,
        tracking_no=shipment.tracking_no,
        shipped_at=shipment.shipped_at,
        delivered_at=shipment.delivered_at,
        created_at=shipment.created_at,
        updated_at=shipment.updated_at
    )

@app.get("/v1/shipments/order/{order_id}", response_model=ShipmentResponse)
async def get_shipment_by_order(order_id: int, db: Session = Depends(get_db)):
    """Get shipment by order ID"""
    shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found for order")
    
    return ShipmentResponse(
        shipment_id=shipment.shipment_id,
        order_id=shipment.order_id,
        carrier=shipment.carrier,
        status=shipment.status,
        tracking_no=shipment.tracking_no,
        shipped_at=shipment.shipped_at,
        delivered_at=shipment.delivered_at,
        created_at=shipment.created_at,
        updated_at=shipment.updated_at
    )

@app.get("/v1/shipments/tracking/{tracking_no}", response_model=TrackingResponse)
async def track_shipment(tracking_no: str, db: Session = Depends(get_db)):
    """Track shipment by tracking number"""
    shipment = db.query(Shipment).filter(Shipment.tracking_no == tracking_no).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    events = db.query(ShipmentEvent).filter(
        ShipmentEvent.shipment_id == shipment.shipment_id
    ).order_by(ShipmentEvent.created_at.asc()).all()
    
    return TrackingResponse(
        shipment=ShipmentResponse(
            shipment_id=shipment.shipment_id,
            order_id=shipment.order_id,
            carrier=shipment.carrier,
            status=shipment.status,
            tracking_no=shipment.tracking_no,
            shipped_at=shipment.shipped_at,
            delivered_at=shipment.delivered_at,
            created_at=shipment.created_at,
            updated_at=shipment.updated_at
        ),
        events=[
            TrackingEvent(
                event_id=e.event_id,
                status=e.status,
                location=e.location,
                description=e.description,
                created_at=e.created_at
            )
            for e in events
        ]
    )

@app.patch("/v1/shipments/{shipment_id}/status", response_model=ShipmentResponse)
async def update_shipment_status(
    shipment_id: int,
    request: UpdateStatusRequest,
    db: Session = Depends(get_db)
):
    """
    Update shipment status and create tracking event
    """
    try:
        shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
        if not shipment:
            raise HTTPException(status_code=404, detail="Shipment not found")
        
        # Update shipment status
        old_status = shipment.status
        shipment.status = request.status.value
        shipment.updated_at = datetime.utcnow()
        
        # Update timestamps based on status
        if request.status == ShipmentStatus.SHIPPED and not shipment.shipped_at:
            shipment.shipped_at = datetime.utcnow()
        elif request.status == ShipmentStatus.DELIVERED and not shipment.delivered_at:
            shipment.delivered_at = datetime.utcnow()
            SHIPMENTS_DELIVERED.inc()
        elif request.status == ShipmentStatus.FAILED:
            SHIPMENTS_FAILED.inc()
        
        # Update metrics
        STATUS_UPDATES.inc()
        API_REQUESTS.labels(method='PATCH', endpoint='/v1/shipments/status', status='200').inc()
        
        # Create tracking event
        event = ShipmentEvent(
            shipment_id=shipment_id,
            status=request.status.value,
            location=request.location,
            description=request.description or f"Status updated from {old_status} to {request.status.value}"
        )
        db.add(event)
        
        db.commit()
        db.refresh(shipment)
        
        logger.info(json.dumps({
            "event": "status_updated",
            "shipment_id": shipment_id,
            "old_status": old_status,
            "new_status": request.status.value,
            "location": request.location
        }))
        
        return ShipmentResponse(
            shipment_id=shipment.shipment_id,
            order_id=shipment.order_id,
            carrier=shipment.carrier,
            status=shipment.status,
            tracking_no=shipment.tracking_no,
            shipped_at=shipment.shipped_at,
            delivered_at=shipment.delivered_at,
            created_at=shipment.created_at,
            updated_at=shipment.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update shipment status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/v1/shipments/{shipment_id}")
async def cancel_shipment(shipment_id: int, db: Session = Depends(get_db)):
    """Cancel a shipment"""
    try:
        shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
        if not shipment:
            raise HTTPException(status_code=404, detail="Shipment not found")
        
        if shipment.status in [ShipmentStatus.DELIVERED.value, ShipmentStatus.CANCELLED.value]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel shipment with status: {shipment.status}"
            )
        
        shipment.status = ShipmentStatus.CANCELLED.value
        shipment.updated_at = datetime.utcnow()
        
        event = ShipmentEvent(
            shipment_id=shipment_id,
            status=ShipmentStatus.CANCELLED.value,
            description="Shipment cancelled"
        )
        db.add(event)
        
        db.commit()
        
        # Update metrics
        SHIPMENTS_CANCELLED.inc()
        API_REQUESTS.labels(method='DELETE', endpoint='/v1/shipments', status='200').inc()
        
        # Notify inventory to release reservations
        await notify_inventory_release(shipment.order_id, "Shipment cancelled")
        
        logger.info(json.dumps({
            "event": "shipment_cancelled",
            "shipment_id": shipment_id,
            "previous_status": shipment.status
        }))
        
        return {"message": "Shipment cancelled successfully", "shipment_id": shipment_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to cancel shipment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/shipments", response_model=List[ShipmentResponse])
async def list_shipments(
    status: Optional[ShipmentStatus] = None,
    carrier: Optional[Carrier] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List shipments with filters and pagination"""
    query = db.query(Shipment)
    
    if status:
        query = query.filter(Shipment.status == status.value)
    if carrier:
        query = query.filter(Shipment.carrier == carrier.value)
    
    shipments = query.offset(skip).limit(limit).all()
    
    return [
        ShipmentResponse(
            shipment_id=s.shipment_id,
            order_id=s.order_id,
            carrier=s.carrier,
            status=s.status,
            tracking_no=s.tracking_no,
            shipped_at=s.shipped_at,
            delivered_at=s.delivered_at,
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in shipments
    ]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "shipping-service", "timestamp": datetime.utcnow()}

@app.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """Get Prometheus metrics"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/metrics/summary")
async def get_metrics_summary(db: Session = Depends(get_db)):
    """Get service metrics summary for monitoring dashboard"""
    try:
        # Database metrics
        total_shipments = db.query(func.count(Shipment.shipment_id)).scalar()
        pending_shipments = db.query(func.count(Shipment.shipment_id)).filter(
            Shipment.status == ShipmentStatus.PENDING.value
        ).scalar()
        in_transit_shipments = db.query(func.count(Shipment.shipment_id)).filter(
            Shipment.status.in_([
                ShipmentStatus.SHIPPED.value,
                ShipmentStatus.IN_TRANSIT.value,
                ShipmentStatus.OUT_FOR_DELIVERY.value
            ])
        ).scalar()
        delivered_shipments = db.query(func.count(Shipment.shipment_id)).filter(
            Shipment.status == ShipmentStatus.DELIVERED.value
        ).scalar()
        failed_shipments = db.query(func.count(Shipment.shipment_id)).filter(
            Shipment.status == ShipmentStatus.FAILED.value
        ).scalar()
        
        return {
            "service": "shipping-service",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "operational",
            "database_metrics": {
                "total_shipments": total_shipments,
                "pending_shipments": pending_shipments,
                "in_transit_shipments": in_transit_shipments,
                "delivered_shipments": delivered_shipments,
                "failed_shipments": failed_shipments
            }
        }
    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}")
        return {
            "service": "shipping-service",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e)
        }
