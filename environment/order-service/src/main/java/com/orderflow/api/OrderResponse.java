package com.orderflow.api;

import com.orderflow.domain.Order;
import com.orderflow.domain.OrderStatus;

import java.io.Serializable;
import java.time.Instant;
import java.util.UUID;

/**
 * Wire shape for an order. This is also what gets stored in the Redis cache,
 * which is why it implements Serializable and stays flat.
 */
public record OrderResponse(
        UUID id,
        String customerId,
        OrderStatus status,
        long totalCents,
        String currency,
        long lastEventSequence,
        Instant statusUpdatedAt,
        Instant createdAt,
        Instant updatedAt
) implements Serializable {

    public static OrderResponse from(Order o) {
        return new OrderResponse(
                o.getId(),
                o.getCustomerId(),
                o.getStatus(),
                o.getTotalCents(),
                o.getCurrency(),
                o.getLastEventSequence(),
                o.getStatusUpdatedAt(),
                o.getCreatedAt(),
                o.getUpdatedAt()
        );
    }
}
