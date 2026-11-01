package com.orderflow.service;

import com.orderflow.api.CreateOrderRequest;
import com.orderflow.domain.Order;
import com.orderflow.domain.OrderRepository;
import com.orderflow.messaging.OrderEventPublisher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Instant;
import java.util.Optional;

@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    private final OrderRepository orders;
    private final OrderEventPublisher publisher;
    private final Clock clock;

    public OrderService(OrderRepository orders, OrderEventPublisher publisher, Clock clock) {
        this.orders = orders;
        this.publisher = publisher;
        this.clock = clock;
    }

    @Transactional
    public CreateOrderResult createOrder(String idempotencyKey, CreateOrderRequest request) {
        String fingerprint = RequestFingerprint.of(request);

        Optional<Order> existing = orders.findByIdempotencyKey(idempotencyKey);
        if (existing.isPresent()) {
            Order found = existing.get();
            if (!found.getRequestFingerprint().equals(fingerprint)) {
                throw new IdempotencyKeyReusedException(idempotencyKey);
            }
            log.debug("replaying order {} for key {}", found.getId(), idempotencyKey);
            return CreateOrderResult.replay(found);
        }

        Instant now = clock.instant();
        Order order = Order.create(request.customerId(), idempotencyKey, fingerprint,
                request.totalCents(), request.currency(), now);

        // Downstream (fulfillment, notifications) must hear about the order before
        // we answer the client, otherwise a fast follow-up status event can arrive
        // for an order nobody knows about yet.
        publisher.publishOrderCreated(order);

        orders.save(order);
        log.info("created order {} for customer {}", order.getId(), order.getCustomerId());
        return CreateOrderResult.created(order);
    }
}
