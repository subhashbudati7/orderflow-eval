package com.orderflow.service;

import com.orderflow.domain.Order;
import com.orderflow.domain.OrderRepository;
import com.orderflow.domain.OrderStatus;
import com.orderflow.domain.OrderStatusHistory;
import com.orderflow.domain.OrderStatusHistoryRepository;
import com.orderflow.messaging.OrderStatusEvent;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class OrderStatusServiceTest {

    private static final Instant NOW = Instant.parse("2026-03-01T12:00:00Z");

    @Mock
    OrderRepository orders;

    @Mock
    OrderStatusHistoryRepository history;

    OrderStatusService service;

    Order order;

    @BeforeEach
    void setUp() {
        service = new OrderStatusService(orders, history, Clock.fixed(NOW, ZoneOffset.UTC));
        order = Order.create("cust-1", "k", "fp", 100, "USD", NOW.minusSeconds(60));
    }

    @Test
    void appliesStatusAndRecordsHistory() {
        when(orders.findById(order.getId())).thenReturn(Optional.of(order));
        Instant occurred = NOW.minusSeconds(5);

        service.applyStatusUpdate(new OrderStatusEvent(order.getId(), OrderStatus.PAID, 1, occurred, "payments"));

        assertThat(order.getStatus()).isEqualTo(OrderStatus.PAID);
        assertThat(order.getLastEventSequence()).isEqualTo(1);
        assertThat(order.getStatusUpdatedAt()).isEqualTo(occurred);
        assertThat(order.getUpdatedAt()).isEqualTo(NOW);

        ArgumentCaptor<OrderStatusHistory> captor = ArgumentCaptor.forClass(OrderStatusHistory.class);
        verify(history).save(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo(OrderStatus.PAID);
        assertThat(captor.getValue().getEventSequence()).isEqualTo(1);
        assertThat(captor.getValue().getSource()).isEqualTo("payments");
    }

    @Test
    void unknownOrderThrows() {
        UUID missing = UUID.randomUUID();
        when(orders.findById(missing)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.applyStatusUpdate(
                new OrderStatusEvent(missing, OrderStatus.PAID, 1, NOW, "payments")))
                .isInstanceOf(OrderNotFoundException.class);
        verify(history, org.mockito.Mockito.never()).save(any());
    }
}
