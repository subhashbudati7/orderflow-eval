package com.orderflow.domain;

/**
 * Status values the order can carry. The order service does not enforce a
 * state machine over these; fulfillment owns the transitions and tells us
 * about them via order.status-updates. See docs/ARCHITECTURE.md.
 */
public enum OrderStatus {
    CREATED,
    PAYMENT_PENDING,
    PAID,
    PICKING,
    SHIPPED,
    DELIVERED,
    CANCELLED
}
