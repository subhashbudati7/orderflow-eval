package com.orderflow.service;

import com.orderflow.api.CreateOrderRequest;
import com.orderflow.api.CreateOrderRequest.LineItem;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class RequestFingerprintTest {

    @Test
    void itemOrderDoesNotChangeFingerprint() {
        var a = new CreateOrderRequest("c1", List.of(
                new LineItem("SKU-A", 1, 100),
                new LineItem("SKU-B", 2, 50)), "USD");
        var b = new CreateOrderRequest("c1", List.of(
                new LineItem("SKU-B", 2, 50),
                new LineItem("SKU-A", 1, 100)), "USD");

        assertThat(RequestFingerprint.of(a)).isEqualTo(RequestFingerprint.of(b));
    }

    @Test
    void quantityChangeChangesFingerprint() {
        var a = new CreateOrderRequest("c1", List.of(new LineItem("SKU-A", 1, 100)), "USD");
        var b = new CreateOrderRequest("c1", List.of(new LineItem("SKU-A", 2, 100)), "USD");

        assertThat(RequestFingerprint.of(a)).isNotEqualTo(RequestFingerprint.of(b));
    }

    @Test
    void fingerprintIsHex256() {
        var a = new CreateOrderRequest("c1", List.of(new LineItem("SKU-A", 1, 100)), "USD");
        assertThat(RequestFingerprint.of(a)).matches("[0-9a-f]{64}");
    }
}
