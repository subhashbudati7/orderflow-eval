package com.orderflow.messaging;

import com.orderflow.domain.OrderStatus;

import java.time.Instant;
import java.util.UUID;

/**
 * Message on order.status-updates. Produced by fulfillment.
 *
 * sequence is per order and strictly increasing on the producer side.
 * occurredAt is the producer's wall clock when the transition happened.
 */
public record OrderStatusEvent(
        UUID orderId,
        OrderStatus status,
        long sequence,
        Instant occurredAt,
        String source
) {
}
