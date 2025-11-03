-- Shipping Service Database Schema

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL UNIQUE,
    carrier VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    tracking_no VARCHAR(50) UNIQUE NOT NULL,
    shipped_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_shipments_order_id ON shipments(order_id);
CREATE INDEX idx_shipments_status ON shipments(status);
CREATE INDEX idx_shipments_tracking_no ON shipments(tracking_no);

CREATE TABLE IF NOT EXISTS shipment_events (
    event_id SERIAL PRIMARY KEY,
    shipment_id INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    location VARCHAR(200),
    description VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_shipment_events_shipment_id ON shipment_events(shipment_id);

-- Idempotency keys table for preventing duplicate operations
CREATE TABLE IF NOT EXISTS idempotency_keys (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    response_data VARCHAR(2000) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_idempotency_key ON idempotency_keys(key);
CREATE INDEX idx_expires_at ON idempotency_keys(expires_at);

-- Comments for documentation
COMMENT ON TABLE shipments IS 'Stores shipment information for orders';
COMMENT ON TABLE shipment_events IS 'Tracks shipment status changes and location updates';
COMMENT ON TABLE idempotency_keys IS 'Ensures idempotent API operations';
