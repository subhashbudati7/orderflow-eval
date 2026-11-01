package com.orderflow.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "orders")
public class Order {

    @Id
    private UUID id;

    @Column(name = "customer_id", nullable = false)
    private String customerId;

    @Column(name = "idempotency_key", nullable = false)
    private String idempotencyKey;

    /** SHA-256 of the canonical request body, used to detect key reuse with a different payload. */
    @Column(name = "request_fingerprint", nullable = false)
    private String requestFingerprint;

    @Column(name = "total_cents", nullable = false)
    private long totalCents;

    @Column(nullable = false, length = 3)
    private String currency;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private OrderStatus status;

    @Column(name = "last_event_sequence", nullable = false)
    private long lastEventSequence;

    @Column(name = "status_updated_at", nullable = false)
    private Instant statusUpdatedAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected Order() {
    }

    public static Order create(String customerId, String idempotencyKey, String fingerprint,
                               long totalCents, String currency, Instant now) {
        Order o = new Order();
        o.id = UUID.randomUUID();
        o.customerId = customerId;
        o.idempotencyKey = idempotencyKey;
        o.requestFingerprint = fingerprint;
        o.totalCents = totalCents;
        o.currency = currency;
        o.status = OrderStatus.CREATED;
        o.lastEventSequence = 0L;
        o.statusUpdatedAt = now;
        o.createdAt = now;
        o.updatedAt = now;
        return o;
    }

    public void applyStatus(OrderStatus newStatus, long sequence, Instant occurredAt, Instant now) {
        this.status = newStatus;
        this.lastEventSequence = sequence;
        this.statusUpdatedAt = occurredAt;
        this.updatedAt = now;
    }

    public UUID getId() {
        return id;
    }

    public String getCustomerId() {
        return customerId;
    }

    public String getIdempotencyKey() {
        return idempotencyKey;
    }

    public String getRequestFingerprint() {
        return requestFingerprint;
    }

    public long getTotalCents() {
        return totalCents;
    }

    public String getCurrency() {
        return currency;
    }

    public OrderStatus getStatus() {
        return status;
    }

    public long getLastEventSequence() {
        return lastEventSequence;
    }

    public Instant getStatusUpdatedAt() {
        return statusUpdatedAt;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }
}
