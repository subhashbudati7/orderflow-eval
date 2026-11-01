package com.orderflow.service;

import com.orderflow.api.OrderResponse;
import com.orderflow.api.StatusHistoryEntry;
import com.orderflow.domain.OrderRepository;
import com.orderflow.domain.OrderStatusHistoryRepository;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
public class OrderQueryService {

    public static final String ORDERS_CACHE = "orders";

    private final OrderRepository orders;
    private final OrderStatusHistoryRepository history;

    public OrderQueryService(OrderRepository orders, OrderStatusHistoryRepository history) {
        this.orders = orders;
        this.history = history;
    }

    @Cacheable(value = ORDERS_CACHE, key = "#id")
    @Transactional(readOnly = true)
    public OrderResponse getOrder(UUID id) {
        return orders.findById(id)
                .map(OrderResponse::from)
                .orElseThrow(() -> new OrderNotFoundException(id));
    }

    @Transactional(readOnly = true)
    public List<StatusHistoryEntry> getHistory(UUID id) {
        if (!orders.existsById(id)) {
            throw new OrderNotFoundException(id);
        }
        return history.findByOrderIdOrderByEventSequenceAsc(id).stream()
                .map(StatusHistoryEntry::from)
                .toList();
    }
}
