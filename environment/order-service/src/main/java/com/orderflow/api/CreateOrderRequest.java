package com.orderflow.api;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;

import java.util.List;

public record CreateOrderRequest(
        @NotBlank String customerId,
        @NotEmpty List<@Valid LineItem> items,
        @NotBlank @Pattern(regexp = "[A-Z]{3}") String currency
) {

    public record LineItem(
            @NotBlank String sku,
            @Min(1) int quantity,
            @Min(0) long unitPriceCents
    ) {
    }

    public long totalCents() {
        long total = 0;
        for (LineItem item : items) {
            total += (long) item.quantity() * item.unitPriceCents();
        }
        return total;
    }
}
