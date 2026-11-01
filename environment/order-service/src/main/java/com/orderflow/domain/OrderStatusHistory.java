package com.orderflow.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

/** One row per status event we actually applied to an order. */
@Entity
@Table(name = "order_status_history")
public class OrderStatusHistory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_id", nullable = false)
    private UUID orderId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private OrderStatus status;

    @Column(name = "event_sequence", nullable = false)
    private long eventSequence;

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt;

    @Column(name = "recorded_at", nullable = false)
    private Instant recordedAt;

    @Column(length = 64)
    private String source;

    protected OrderStatusHistory() {
    }

    public OrderStatusHistory(UUID orderId, OrderStatus status, long eventSequence,
                              Instant occurredAt, Instant recordedAt, String source) {
        this.orderId = orderId;
        this.status = status;
        this.eventSequence = eventSequence;
        this.occurredAt = occurredAt;
        this.recordedAt = recordedAt;
        this.source = source;
    }

    public Long getId() {
        return id;
    }

    public UUID getOrderId() {
        return orderId;
    }

    public OrderStatus getStatus() {
        return status;
    }

    public long getEventSequence() {
        return eventSequence;
    }

    public Instant getOccurredAt() {
        return occurredAt;
    }

    public Instant getRecordedAt() {
        return recordedAt;
    }

    public String getSource() {
        return source;
    }
}
