CREATE TABLE orders (
    id                  UUID PRIMARY KEY,
    customer_id         VARCHAR(64)  NOT NULL,
    idempotency_key     VARCHAR(128) NOT NULL,
    request_fingerprint VARCHAR(64)  NOT NULL,
    total_cents         BIGINT       NOT NULL,
    currency            VARCHAR(3)   NOT NULL,
    status              VARCHAR(32)  NOT NULL,
    last_event_sequence BIGINT       NOT NULL DEFAULT 0,
    status_updated_at   TIMESTAMPTZ  NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL,
    updated_at          TIMESTAMPTZ  NOT NULL
);

-- lookups by key happen on every create, keep them cheap
CREATE INDEX idx_orders_idempotency_key ON orders (idempotency_key);
CREATE INDEX idx_orders_customer_id ON orders (customer_id);

CREATE TABLE order_status_history (
    id              BIGSERIAL PRIMARY KEY,
    order_id        UUID        NOT NULL REFERENCES orders (id),
    status          VARCHAR(32) NOT NULL,
    event_sequence  BIGINT      NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL,
    source          VARCHAR(64)
);

CREATE INDEX idx_order_status_history_order_id ON order_status_history (order_id, event_sequence);
