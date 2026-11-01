package com.orderflow.api;

import com.orderflow.domain.Order;
import com.orderflow.service.CreateOrderResult;
import com.orderflow.service.IdempotencyKeyReusedException;
import com.orderflow.service.OrderNotFoundException;
import com.orderflow.service.OrderQueryService;
import com.orderflow.service.OrderService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.cache.CacheManager;
import org.springframework.cache.concurrent.ConcurrentMapCacheManager;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(OrderController.class)
@Import(OrderControllerTest.CacheStub.class)
class OrderControllerTest {

    @TestConfiguration
    static class CacheStub {
        @Bean
        CacheManager cacheManager() {
            return new ConcurrentMapCacheManager();
        }
    }

    private static final String BODY = """
            {"customerId":"cust-1","currency":"USD",
             "items":[{"sku":"SKU-1","quantity":2,"unitPriceCents":1250}]}
            """;

    @Autowired
    MockMvc mvc;

    @MockitoBean
    OrderService orderService;

    @MockitoBean
    OrderQueryService queryService;

    private Order sampleOrder() {
        return Order.create("cust-1", "key-1", "fp", 2500, "USD", Instant.parse("2026-03-01T10:00:00Z"));
    }

    @Test
    void firstCreateReturns201WithLocation() throws Exception {
        Order order = sampleOrder();
        when(orderService.createOrder(eq("key-1"), any())).thenReturn(CreateOrderResult.created(order));

        mvc.perform(post("/orders")
                        .header("Idempotency-Key", "key-1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(BODY))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "/orders/" + order.getId()))
                .andExpect(header().doesNotExist("Idempotent-Replayed"))
                .andExpect(jsonPath("$.id").value(order.getId().toString()))
                .andExpect(jsonPath("$.status").value("CREATED"))
                .andExpect(jsonPath("$.totalCents").value(2500));
    }

    @Test
    void replayReturns200WithReplayedHeader() throws Exception {
        Order order = sampleOrder();
        when(orderService.createOrder(eq("key-1"), any())).thenReturn(CreateOrderResult.replay(order));

        mvc.perform(post("/orders")
                        .header("Idempotency-Key", "key-1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(BODY))
                .andExpect(status().isOk())
                .andExpect(header().string("Idempotent-Replayed", "true"))
                .andExpect(jsonPath("$.id").value(order.getId().toString()));
    }

    @Test
    void missingIdempotencyKeyIs400() throws Exception {
        mvc.perform(post("/orders")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(BODY))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("MISSING_HEADER"));
    }

    @Test
    void keyReusedWithDifferentBodyIs422() throws Exception {
        when(orderService.createOrder(eq("key-1"), any()))
                .thenThrow(new IdempotencyKeyReusedException("key-1"));

        mvc.perform(post("/orders")
                        .header("Idempotency-Key", "key-1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(BODY))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.code").value("IDEMPOTENCY_KEY_REUSED"));
    }

    @Test
    void emptyItemsIs400() throws Exception {
        mvc.perform(post("/orders")
                        .header("Idempotency-Key", "key-1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"customerId\":\"c\",\"currency\":\"USD\",\"items\":[]}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"));
    }

    @Test
    void unknownOrderIs404() throws Exception {
        UUID id = UUID.randomUUID();
        when(queryService.getOrder(id)).thenThrow(new OrderNotFoundException(id));

        mvc.perform(get("/orders/" + id))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("ORDER_NOT_FOUND"));
    }
}
