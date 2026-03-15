-- Users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    role VARCHAR DEFAULT 'user'
);

-- Properties
CREATE TABLE IF NOT EXISTS properties (
    id SERIAL PRIMARY KEY,
    state VARCHAR NOT NULL,
    district VARCHAR NOT NULL,
    tehsil VARCHAR NOT NULL,
    village VARCHAR NOT NULL,
    plot_no VARCHAR NOT NULL,
    house_no VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uix_property_location UNIQUE (state, district, tehsil, village, plot_no, house_no)
);

-- People
CREATE TABLE IF NOT EXISTS people (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    pan_number VARCHAR UNIQUE,
    aadhaar_number VARCHAR UNIQUE,
    role VARCHAR
);

-- Documents
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR NOT NULL,
    file_hash VARCHAR UNIQUE NOT NULL,
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id),
    seller_id INTEGER REFERENCES people(id),
    buyer_id INTEGER REFERENCES people(id),
    document_id INTEGER REFERENCES documents(id),
    registration_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat History
CREATE TABLE IF NOT EXISTS chat_sessions (
    id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR REFERENCES chat_sessions(id),
    role VARCHAR NOT NULL,
    content VARCHAR NOT NULL,
    reasoning_details JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
