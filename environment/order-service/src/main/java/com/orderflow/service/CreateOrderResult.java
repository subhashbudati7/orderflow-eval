package com.orderflow.service;

import com.orderflow.domain.Order;

/** replayed == true means we matched an existing order on the idempotency key. */
public record CreateOrderResult(Order order, boolean replayed) {

    public static CreateOrderResult created(Order order) {
        return new CreateOrderResult(order, false);
    }

    public static CreateOrderResult replay(Order order) {
        return new CreateOrderResult(order, true);
    }
}
