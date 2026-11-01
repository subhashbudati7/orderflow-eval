package com.orderflow.api;

import com.orderflow.service.CreateOrderResult;
import com.orderflow.service.OrderQueryService;
import com.orderflow.service.OrderService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/orders")
public class OrderController {

    public static final String IDEMPOTENCY_HEADER = "Idempotency-Key";
    public static final String REPLAYED_HEADER = "Idempotent-Replayed";

    private final OrderService orderService;
    private final OrderQueryService queryService;

    public OrderController(OrderService orderService, OrderQueryService queryService) {
        this.orderService = orderService;
        this.queryService = queryService;
    }

    @PostMapping
    public ResponseEntity<OrderResponse> create(
            @RequestHeader(IDEMPOTENCY_HEADER) String idempotencyKey,
            @Valid @RequestBody CreateOrderRequest request) {

        CreateOrderResult result = orderService.createOrder(idempotencyKey, request);
        OrderResponse body = OrderResponse.from(result.order());

        if (result.replayed()) {
            return ResponseEntity.ok()
                    .header(REPLAYED_HEADER, "true")
                    .body(body);
        }
        return ResponseEntity.status(HttpStatus.CREATED)
                .location(URI.create("/orders/" + body.id()))
                .body(body);
    }

    @GetMapping("/{id}")
    public OrderResponse get(@PathVariable UUID id) {
        return queryService.getOrder(id);
    }

    @GetMapping("/{id}/history")
    public List<StatusHistoryEntry> history(@PathVariable UUID id) {
        return queryService.getHistory(id);
    }
}
