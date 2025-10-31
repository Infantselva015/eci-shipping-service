from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging
import json

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Metrics storage (in-memory for simplicity, use Prometheus in production)
metrics = {
    "shipments_created_total": 0,
    "shipments_delivered_total": 0,
    "shipments_cancelled_total": 0,
    "shipments_failed_total": 0,
    "status_updates_total": 0
}

# Database setup
DATABASE_URL = "postgresql://user:password@shipping-db:5432/shipping_db"
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

# Pydantic schemas
class CreateShipmentRequest(BaseModel):
    order_id: int
    carrier: Carrier = Field(default=Carrier.DHL)
    shipping_address: Optional[dict] = None

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
def generate_tracking_number():
    """Generate unique tracking number"""
    import random
    return f"TRK{random.randint(1000, 9999)}"

def select_carrier() -> str:
    """Select carrier based on availability (can be enhanced with logic)"""
    import random
    return random.choice([c.value for c in Carrier])

# API Endpoints

@app.post("/v1/shipments", response_model=CreateShipmentResponse, status_code=201)
async def create_shipment(
    request: CreateShipmentRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new shipment for an order
    """
    try:
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
            tracking_no=generate_tracking_number()
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
        metrics["shipments_created_total"] += 1
        
        logger.info(json.dumps({
            "event": "shipment_created",
            "shipment_id": shipment.shipment_id,
            "order_id": request.order_id,
            "carrier": shipment.carrier,
            "tracking_no": shipment.tracking_no
        }))
        
        return CreateShipmentResponse(
            shipment_id=shipment.shipment_id,
            order_id=shipment.order_id,
            carrier=shipment.carrier,
            status=shipment.status,
            tracking_no=shipment.tracking_no,
            created_at=shipment.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create shipment: {str(e)}")
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
            metrics["shipments_delivered_total"] += 1
        elif request.status == ShipmentStatus.FAILED:
            metrics["shipments_failed_total"] += 1
        
        # Update metrics
        metrics["status_updates_total"] += 1
        
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
        metrics["shipments_cancelled_total"] += 1
        
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
    """Get service metrics for monitoring"""
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
        
        return {
            "service": "shipping-service",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "operational",
            "metrics": {
                "shipments_created_total": metrics["shipments_created_total"],
                "shipments_delivered_total": metrics["shipments_delivered_total"],
                "shipments_cancelled_total": metrics["shipments_cancelled_total"],
                "shipments_failed_total": metrics["shipments_failed_total"],
                "status_updates_total": metrics["status_updates_total"],
                "total_shipments_in_db": total_shipments,
                "pending_shipments": pending_shipments,
                "in_transit_shipments": in_transit_shipments
            }
        }
    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}")
        return {
            "service": "shipping-service",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "operational",
            "metrics": metrics
        }
