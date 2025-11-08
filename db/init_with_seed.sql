-- Enhanced Database Schema with Indexes and Sample Data

-- Drop existing tables if they exist
DROP TABLE IF EXISTS shipment_events CASCADE;
DROP TABLE IF EXISTS shipments CASCADE;
DROP TABLE IF EXISTS idempotency_keys CASCADE;

-- Create idempotency_keys table
CREATE TABLE idempotency_keys (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    response_data VARCHAR(2000) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Create indexes for faster lookups
CREATE INDEX idx_idempotency_key ON idempotency_keys(key);
CREATE INDEX idx_idempotency_expires_at ON idempotency_keys(expires_at);

-- Create shipments table
CREATE TABLE shipments (
    shipment_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL UNIQUE,
    carrier VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    tracking_no VARCHAR(50) UNIQUE NOT NULL,
    shipped_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_status CHECK (status IN (
        'PENDING', 'PACKED', 'SHIPPED', 'IN_TRANSIT', 
        'OUT_FOR_DELIVERY', 'DELIVERED', 'FAILED', 'CANCELLED'
    )),
    CONSTRAINT chk_carrier CHECK (carrier IN ('DHL', 'Bluedart', 'FedEx', 'DTDC')),
    CONSTRAINT chk_shipped_at CHECK (shipped_at IS NULL OR shipped_at >= created_at),
    CONSTRAINT chk_delivered_at CHECK (delivered_at IS NULL OR delivered_at >= created_at)
);

-- Create shipment_events table
CREATE TABLE shipment_events (
    event_id SERIAL PRIMARY KEY,
    shipment_id INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    location VARCHAR(200),
    description VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_shipment FOREIGN KEY (shipment_id) 
        REFERENCES shipments(shipment_id) ON DELETE CASCADE,
    CONSTRAINT chk_event_status CHECK (status IN (
        'PENDING', 'PACKED', 'SHIPPED', 'IN_TRANSIT', 
        'OUT_FOR_DELIVERY', 'DELIVERED', 'FAILED', 'CANCELLED'
    ))
);

-- Create indexes for better query performance
CREATE INDEX idx_shipments_order_id ON shipments(order_id);
CREATE INDEX idx_shipments_tracking_no ON shipments(tracking_no);
CREATE INDEX idx_shipments_status ON shipments(status);
CREATE INDEX idx_shipments_carrier ON shipments(carrier);
CREATE INDEX idx_shipments_created_at ON shipments(created_at);
CREATE INDEX idx_shipment_events_shipment_id ON shipment_events(shipment_id);
CREATE INDEX idx_shipment_events_status ON shipment_events(status);
CREATE INDEX idx_shipment_events_created_at ON shipment_events(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_shipments_updated_at
    BEFORE UPDATE ON shipments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for testing (20 shipments)
INSERT INTO shipments (order_id, carrier, status, tracking_no, shipped_at, delivered_at, created_at) VALUES
-- Delivered shipments
(1001, 'DHL', 'DELIVERED', 'TRK1001', '2025-10-29 10:00:00', '2025-10-30 15:30:00', '2025-10-29 09:00:00'),
(1002, 'FedEx', 'DELIVERED', 'TRK1002', '2025-10-28 11:30:00', '2025-10-29 16:00:00', '2025-10-28 10:00:00'),
(1003, 'Bluedart', 'DELIVERED', 'TRK1003', '2025-10-27 09:00:00', '2025-10-28 14:00:00', '2025-10-27 08:00:00'),
(1004, 'DTDC', 'DELIVERED', 'TRK1004', '2025-10-26 10:30:00', '2025-10-27 17:00:00', '2025-10-26 09:30:00'),
(1005, 'DHL', 'DELIVERED', 'TRK1005', '2025-10-25 12:00:00', '2025-10-26 13:30:00', '2025-10-25 11:00:00'),

-- In transit shipments
(1006, 'FedEx', 'IN_TRANSIT', 'TRK1006', '2025-10-30 08:00:00', NULL, '2025-10-30 07:00:00'),
(1007, 'DHL', 'IN_TRANSIT', 'TRK1007', '2025-10-30 09:30:00', NULL, '2025-10-30 08:30:00'),
(1008, 'Bluedart', 'IN_TRANSIT', 'TRK1008', '2025-10-30 10:00:00', NULL, '2025-10-30 09:00:00'),

-- Out for delivery
(1009, 'DTDC', 'OUT_FOR_DELIVERY', 'TRK1009', '2025-10-30 06:00:00', NULL, '2025-10-29 15:00:00'),
(1010, 'DHL', 'OUT_FOR_DELIVERY', 'TRK1010', '2025-10-30 07:00:00', NULL, '2025-10-29 16:00:00'),

-- Shipped
(1011, 'FedEx', 'SHIPPED', 'TRK1011', '2025-10-31 08:00:00', NULL, '2025-10-31 07:00:00'),
(1012, 'Bluedart', 'SHIPPED', 'TRK1012', '2025-10-31 09:00:00', NULL, '2025-10-31 08:00:00'),

-- Packed
(1013, 'DHL', 'PACKED', 'TRK1013', NULL, NULL, '2025-10-31 10:00:00'),
(1014, 'DTDC', 'PACKED', 'TRK1014', NULL, NULL, '2025-10-31 10:30:00'),

-- Pending
(1015, 'FedEx', 'PENDING', 'TRK1015', NULL, NULL, '2025-10-31 11:00:00'),
(1016, 'DHL', 'PENDING', 'TRK1016', NULL, NULL, '2025-10-31 11:30:00'),

-- Failed
(1017, 'Bluedart', 'FAILED', 'TRK1017', '2025-10-29 10:00:00', NULL, '2025-10-29 09:00:00'),

-- Cancelled
(1018, 'DTDC', 'CANCELLED', 'TRK1018', NULL, NULL, '2025-10-28 14:00:00'),

-- Recent shipments
(1019, 'DHL', 'SHIPPED', 'TRK1019', '2025-10-31 12:00:00', NULL, '2025-10-31 11:45:00'),
(1020, 'FedEx', 'PENDING', 'TRK1020', NULL, NULL, '2025-10-31 12:30:00');

-- Insert sample tracking events
-- Shipment 1001 (Delivered)
INSERT INTO shipment_events (shipment_id, status, location, description, created_at) VALUES
(1, 'PENDING', NULL, 'Shipment created', '2025-10-29 09:00:00'),
(1, 'PACKED', 'Warehouse A', 'Items packed and ready for pickup', '2025-10-29 09:30:00'),
(1, 'SHIPPED', 'New York Distribution Center', 'Package picked up by DHL', '2025-10-29 10:00:00'),
(1, 'IN_TRANSIT', 'Chicago Hub', 'In transit to destination', '2025-10-29 18:00:00'),
(1, 'OUT_FOR_DELIVERY', 'Local Distribution Center', 'Out for delivery - arriving today', '2025-10-30 08:00:00'),
(1, 'DELIVERED', 'Customer Address - 123 Main St', 'Successfully delivered to customer', '2025-10-30 15:30:00');

-- Shipment 1002 (Delivered)
INSERT INTO shipment_events (shipment_id, status, location, description, created_at) VALUES
(2, 'PENDING', NULL, 'Shipment created', '2025-10-28 10:00:00'),
(2, 'PACKED', 'Warehouse B', 'Package prepared', '2025-10-28 10:45:00'),
(2, 'SHIPPED', 'LA Distribution Center', 'Picked up by FedEx', '2025-10-28 11:30:00'),
(2, 'IN_TRANSIT', 'Denver Hub', 'In transit', '2025-10-29 06:00:00'),
(2, 'DELIVERED', 'Customer Address', 'Delivered successfully', '2025-10-29 16:00:00');

-- Shipment 1006 (In Transit)
INSERT INTO shipment_events (shipment_id, status, location, description, created_at) VALUES
(6, 'PENDING', NULL, 'Shipment created', '2025-10-30 07:00:00'),
(6, 'PACKED', 'Warehouse C', 'Ready for shipment', '2025-10-30 07:30:00'),
(6, 'SHIPPED', 'Boston Distribution Center', 'Picked up by FedEx', '2025-10-30 08:00:00'),
(6, 'IN_TRANSIT', 'Philadelphia Hub', 'In transit to New York', '2025-10-30 14:00:00');

-- Shipment 1009 (Out for Delivery)
INSERT INTO shipment_events (shipment_id, status, location, description, created_at) VALUES
(9, 'PENDING', NULL, 'Shipment created', '2025-10-29 15:00:00'),
(9, 'PACKED', 'Warehouse D', 'Items packed', '2025-10-29 15:30:00'),
(9, 'SHIPPED', 'Mumbai Distribution Center', 'Picked up by DTDC', '2025-10-30 06:00:00'),
(9, 'IN_TRANSIT', 'Pune Hub', 'In transit', '2025-10-30 12:00:00'),
(9, 'OUT_FOR_DELIVERY', 'Local DC - Mumbai', 'Out for delivery today', '2025-10-31 08:00:00');

-- Shipment 1011 (Shipped)
INSERT INTO shipment_events (shipment_id, status, location, description, created_at) VALUES
(11, 'PENDING', NULL, 'Shipment created', '2025-10-31 07:00:00'),
(11, 'PACKED', 'Warehouse E', 'Ready for pickup', '2025-10-31 07:30:00'),
(11, 'SHIPPED', 'Seattle Distribution Center', 'Picked up by FedEx', '2025-10-31 08:00:00');

-- Shipment 1013 (Packed)
INSERT INTO shipment_events (shipment_id, status, location, description, created_at) VALUES
(13, 'PENDING', NULL, 'Shipment created', '2025-10-31 10:00:00'),
(13, 'PACKED', 'Warehouse F', 'Items packed, awaiting pickup', '2025-10-31 10:30:00');

-- Shipment 1015 (Pending)
INSERT INTO shipment_events (shipment_id, status, location, description, created_at) VALUES
(15, 'PENDING', NULL, 'Shipment created', '2025-10-31 11:00:00');

-- Shipment 1017 (Failed)
INSERT INTO shipment_events (shipment_id, status, location, description, created_at) VALUES
(17, 'PENDING', NULL, 'Shipment created', '2025-10-29 09:00:00'),
(17, 'PACKED', 'Warehouse G', 'Ready for shipment', '2025-10-29 09:30:00'),
(17, 'SHIPPED', 'Bangalore DC', 'Picked up by Bluedart', '2025-10-29 10:00:00'),
(17, 'IN_TRANSIT', 'Hyderabad Hub', 'In transit', '2025-10-29 16:00:00'),
(17, 'FAILED', 'Delivery Area', 'Delivery failed - incorrect address', '2025-10-30 14:00:00');

-- Shipment 1018 (Cancelled)
INSERT INTO shipment_events (shipment_id, status, location, description, created_at) VALUES
(18, 'PENDING', NULL, 'Shipment created', '2025-10-28 14:00:00'),
(18, 'CANCELLED', NULL, 'Shipment cancelled by customer', '2025-10-28 15:00:00');

-- Create view for shipment summary statistics
CREATE OR REPLACE VIEW shipment_summary AS
SELECT 
    carrier,
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (COALESCE(delivered_at, CURRENT_TIMESTAMP) - created_at))) / 3600 as avg_hours
FROM shipments
GROUP BY carrier, status
ORDER BY carrier, status;

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO user;

-- Display summary
SELECT 'Database initialized successfully!' as message;
SELECT 'Total Shipments: ' || COUNT(*) as info FROM shipments;
SELECT 'Total Events: ' || COUNT(*) as info FROM shipment_events;
SELECT * FROM shipment_summary;
