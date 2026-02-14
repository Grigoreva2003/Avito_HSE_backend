-- Migration: V001 - Initial Schema
-- Description: Create tables for sellers and ads

-- Table: sellers
CREATE TABLE sellers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: ads
CREATE TABLE ads (
    id SERIAL PRIMARY KEY,
    seller_id INTEGER NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category INTEGER NOT NULL,
    images_qty INTEGER NOT NULL DEFAULT 0 CHECK (images_qty >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX idx_ads_seller_id ON ads(seller_id);
CREATE INDEX idx_sellers_is_verified ON sellers(is_verified);

-- Comments
COMMENT ON TABLE sellers IS 'Sellers/Users who create advertisements';
COMMENT ON TABLE ads IS 'Advertisements posted by sellers';
COMMENT ON COLUMN sellers.is_verified IS 'Whether the seller is verified (trusted)';
COMMENT ON COLUMN ads.images_qty IS 'Number of images attached to the advertisement';
