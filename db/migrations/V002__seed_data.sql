-- Migration: V002 - Seed Data
-- Description: Insert test data for development

-- Insert test sellers
INSERT INTO sellers (id, name, is_verified) VALUES
    (1, 'Ivan Ivanov', TRUE),
    (2, 'Petr Petrov', TRUE),
    (3, 'Unverified Seller', FALSE),
    (4, 'Maria Sidorova', TRUE),
    (5, 'Sergey Novikov', FALSE);

-- Insert test ads
INSERT INTO ads (id, seller_id, name, description, category, images_qty) VALUES
    (100, 1, 'iPhone 14 Pro', 'Excellent condition, full package, warranty. Used for 6 months.', 1, 5),
    (101, 1, 'MacBook Pro 16', 'Laptop in perfect condition. M1 Pro, 32GB RAM, 1TB SSD.', 2, 8),
    (102, 2, 'Samsung Galaxy S23', 'New phone, not unpacked. Official warranty.', 1, 3),
    (103, 3, 'Nike Sneakers', 'Size 42, good condition', 10, 0),
    (104, 3, 'AirPods Headphones', 'No photos', 5, 0),
    (105, 4, 'Evening Dress', 'Beautiful dress for special occasion, size S. Worn once.', 15, 10),
    (106, 5, 'Mountain Bike', 'Selling bicycle', 20, 1);

-- Reset sequences to avoid conflicts
SELECT setval('sellers_id_seq', (SELECT MAX(id) FROM sellers));
SELECT setval('ads_id_seq', (SELECT MAX(id) FROM ads));
