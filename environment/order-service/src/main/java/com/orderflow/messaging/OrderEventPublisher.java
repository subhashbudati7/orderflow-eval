package com.orderflow.messaging;

import com.orderflow.domain.Order;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

@Component
public class OrderEventPublisher {

    private static final Logger log = LoggerFactory.getLogger(OrderEventPublisher.class);

    private final KafkaTemplate<String, Object> kafka;
    private final String topic;
    private final long ackTimeoutMs;

    public OrderEventPublisher(KafkaTemplate<String, Object> kafka,
                               @Value("${orderflow.topics.order-events}") String topic,
                               @Value("${orderflow.publish.ack-timeout-ms:5000}") long ackTimeoutMs) {
        this.kafka = kafka;
        this.topic = topic;
        this.ackTimeoutMs = ackTimeoutMs;
    }

    /**
     * Blocks until the broker acks. We had silent message loss in the past when
     * this was fire-and-forget, so keep it synchronous.
     */
    public void publishOrderCreated(Order order) {
        OrderCreatedEvent event = OrderCreatedEvent.from(order);
        try {
            kafka.send(topic, order.getId().toString(), event).get(ackTimeoutMs, TimeUnit.MILLISECONDS);
            log.debug("published OrderCreated for {}", order.getId());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("interrupted while publishing OrderCreated", e);
        } catch (ExecutionException | TimeoutException e) {
            throw new IllegalStateException("failed to publish OrderCreated for " + order.getId(), e);
        }
    }
}
