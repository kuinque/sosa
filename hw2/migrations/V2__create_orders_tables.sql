-- user_operations first (no FK to orders)
CREATE TABLE user_operations (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT         NOT NULL,
    operation_type VARCHAR(20)    NOT NULL,
    created_at     TIMESTAMP      NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_operations_user_type ON user_operations (user_id, operation_type);

-- promo_codes
CREATE TABLE promo_codes (
    id               BIGSERIAL PRIMARY KEY,
    code             VARCHAR(20)    NOT NULL UNIQUE,
    discount_type    VARCHAR(20)    NOT NULL,
    discount_value   DECIMAL(12, 2)  NOT NULL,
    min_order_amount DECIMAL(12, 2) NOT NULL,
    max_uses         INTEGER        NOT NULL,
    current_uses     INTEGER        NOT NULL DEFAULT 0,
    valid_from       TIMESTAMP      NOT NULL,
    valid_until      TIMESTAMP      NOT NULL,
    active           BOOLEAN        NOT NULL DEFAULT true
);

-- orders
CREATE TABLE orders (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT         NOT NULL,
    status          VARCHAR(20)    NOT NULL DEFAULT 'CREATED',
    promo_code_id   BIGINT         REFERENCES promo_codes(id),
    total_amount    DECIMAL(12, 2)  NOT NULL,
    discount_amount DECIMAL(12, 2)  NOT NULL DEFAULT 0,
    created_at      TIMESTAMP      NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP      NOT NULL DEFAULT now()
);

CREATE INDEX idx_orders_user_id ON orders (user_id);
CREATE INDEX idx_orders_status ON orders (status);

CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- order_items
CREATE TABLE order_items (
    id             BIGSERIAL PRIMARY KEY,
    order_id       BIGINT         NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id     BIGINT         NOT NULL REFERENCES products(id),
    quantity       INTEGER        NOT NULL,
    price_at_order DECIMAL(12, 2) NOT NULL
);

CREATE INDEX idx_order_items_order_id ON order_items (order_id);
