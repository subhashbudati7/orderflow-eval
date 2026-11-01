package com.orderflow.service;

import com.orderflow.domain.Order;
import com.orderflow.domain.OrderRepository;
import com.orderflow.domain.OrderStatusHistory;
import com.orderflow.domain.OrderStatusHistoryRepository;
import com.orderflow.messaging.OrderStatusEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Instant;
import java.util.UUID;

/**
 * Applies status events coming from fulfillment to the order row and records
 * them in order_status_history.
 */
@Service
public class OrderStatusService {

    private static final Logger log = LoggerFactory.getLogger(OrderStatusService.class);

    private final OrderRepository orders;
    private final OrderStatusHistoryRepository history;
    private final Clock clock;

    public OrderStatusService(OrderRepository orders, OrderStatusHistoryRepository history, Clock clock) {
        this.orders = orders;
        this.history = history;
        this.clock = clock;
    }

    @Transactional
    public void applyStatusUpdate(OrderStatusEvent event) {
        Order order = orders.findById(event.orderId())
                .orElseThrow(() -> new OrderNotFoundException(event.orderId()));

        Instant now = clock.instant();
        order.applyStatus(event.status(), event.sequence(), event.occurredAt(), now);
        orders.save(order);

        history.save(new OrderStatusHistory(order.getId(), event.status(), event.sequence(),
                event.occurredAt(), now, event.source()));

        evictCachedOrder(order.getId());
        log.info("order {} -> {} (seq {})", order.getId(), event.status(), event.sequence());
    }

    @CacheEvict(value = OrderQueryService.ORDERS_CACHE, key = "#orderId")
    public void evictCachedOrder(UUID orderId) {
        // Eviction is handled by the annotation; nothing else to do here.
        log.debug("evicted cached order {}", orderId);
    }
}
