package com.orderflow.messaging;

import com.orderflow.service.OrderNotFoundException;
import com.orderflow.service.OrderStatusService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class OrderStatusConsumer {

    private static final Logger log = LoggerFactory.getLogger(OrderStatusConsumer.class);

    private final OrderStatusService statusService;

    public OrderStatusConsumer(OrderStatusService statusService) {
        this.statusService = statusService;
    }

    @KafkaListener(
            topics = "${orderflow.topics.order-status-updates}",
            groupId = "${spring.kafka.consumer.group-id}",
            containerFactory = "statusListenerFactory"
    )
    public void onStatusUpdate(OrderStatusEvent event) {
        try {
            statusService.applyStatusUpdate(event);
        } catch (OrderNotFoundException e) {
            // Fulfillment occasionally emits for orders we never persisted (cancelled mid-flight).
            // Nothing to apply; don't poison the partition over it.
            log.warn("dropping status event for unknown order {}", event.orderId());
        }
    }
}
