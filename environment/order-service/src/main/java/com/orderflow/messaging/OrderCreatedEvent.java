package com.orderflow.messaging;

import com.orderflow.domain.Order;

import java.time.Instant;
import java.util.UUID;

/** Message on order.events, emitted once per new order. */
public record OrderCreatedEvent(
        String type,
        UUID orderId,
        String customerId,
        long totalCents,
        String currency,
        String idempotencyKey,
        Instant createdAt
) {

    public static OrderCreatedEvent from(Order o) {
        return new OrderCreatedEvent("OrderCreated", o.getId(), o.getCustomerId(), o.getTotalCents(),
                o.getCurrency(), o.getIdempotencyKey(), o.getCreatedAt());
    }
}
