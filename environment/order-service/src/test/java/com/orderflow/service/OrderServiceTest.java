package com.orderflow.service;

import com.orderflow.api.CreateOrderRequest;
import com.orderflow.api.CreateOrderRequest.LineItem;
import com.orderflow.domain.Order;
import com.orderflow.domain.OrderRepository;
import com.orderflow.messaging.OrderEventPublisher;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    private static final Instant NOW = Instant.parse("2026-03-01T10:00:00Z");

    @Mock
    OrderRepository orders;

    @Mock
    OrderEventPublisher publisher;

    OrderService service;

    final CreateOrderRequest request = new CreateOrderRequest("cust-7",
            List.of(new LineItem("SKU-1", 3, 400)), "EUR");

    @BeforeEach
    void setUp() {
        service = new OrderService(orders, publisher, Clock.fixed(NOW, ZoneOffset.UTC));
    }

    @Test
    void newKeyCreatesOrderAndPublishes() {
        when(orders.findByIdempotencyKey("k1")).thenReturn(Optional.empty());
        when(orders.save(any())).thenAnswer(inv -> inv.getArgument(0));

        CreateOrderResult result = service.createOrder("k1", request);

        assertThat(result.replayed()).isFalse();
        assertThat(result.order().getTotalCents()).isEqualTo(1200);
        assertThat(result.order().getCurrency()).isEqualTo("EUR");
        assertThat(result.order().getCreatedAt()).isEqualTo(NOW);
        verify(publisher).publishOrderCreated(result.order());
        verify(orders).save(result.order());
    }

    @Test
    void sameKeySameBodyReplaysWithoutPublishing() {
        Order existing = Order.create("cust-7", "k1", RequestFingerprint.of(request), 1200, "EUR", NOW);
        when(orders.findByIdempotencyKey("k1")).thenReturn(Optional.of(existing));

        CreateOrderResult result = service.createOrder("k1", request);

        assertThat(result.replayed()).isTrue();
        assertThat(result.order()).isSameAs(existing);
        verify(publisher, never()).publishOrderCreated(any());
        verify(orders, never()).save(any());
    }

    @Test
    void sameKeyDifferentBodyIsRejected() {
        Order existing = Order.create("cust-7", "k1", "some-other-fingerprint", 999, "EUR", NOW);
        when(orders.findByIdempotencyKey("k1")).thenReturn(Optional.of(existing));

        assertThatThrownBy(() -> service.createOrder("k1", request))
                .isInstanceOf(IdempotencyKeyReusedException.class);
        verify(publisher, never()).publishOrderCreated(any());
    }
}
