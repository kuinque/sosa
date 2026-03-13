CREATE TABLE products (
    id         BIGSERIAL PRIMARY KEY,
    name       VARCHAR(255)   NOT NULL,
    description VARCHAR(4000),
    price      DECIMAL(12, 2) NOT NULL,
    stock      INTEGER        NOT NULL DEFAULT 0,
    category   VARCHAR(100)   NOT NULL,
    status     VARCHAR(20)    NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP      NOT NULL DEFAULT now(),
    updated_at TIMESTAMP      NOT NULL DEFAULT now()
);

CREATE INDEX idx_products_status ON products (status);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
