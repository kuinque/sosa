ALTER TABLE products ADD COLUMN seller_id BIGINT REFERENCES users(id);
