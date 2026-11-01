package com.orderflow.api;

import com.orderflow.domain.OrderStatus;
import com.orderflow.domain.OrderStatusHistory;

import java.time.Instant;

public record StatusHistoryEntry(
        OrderStatus status,
        long sequence,
        Instant occurredAt,
        Instant recordedAt,
        String source
) {

    public static StatusHistoryEntry from(OrderStatusHistory h) {
        return new StatusHistoryEntry(h.getStatus(), h.getEventSequence(), h.getOccurredAt(),
                h.getRecordedAt(), h.getSource());
    }
}
