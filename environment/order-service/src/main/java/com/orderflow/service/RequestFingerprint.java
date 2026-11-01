package com.orderflow.service;

import com.orderflow.api.CreateOrderRequest;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.stream.Collectors;

/**
 * Canonical hash of a create request so we can tell "same key, same body"
 * (a retry) from "same key, different body" (a client bug).
 */
public final class RequestFingerprint {

    private RequestFingerprint() {
    }

    public static String of(CreateOrderRequest req) {
        String items = req.items().stream()
                .sorted((a, b) -> a.sku().compareTo(b.sku()))
                .map(i -> i.sku() + "x" + i.quantity() + "@" + i.unitPriceCents())
                .collect(Collectors.joining(","));
        String canonical = req.customerId() + "|" + req.currency() + "|" + items;
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(md.digest(canonical.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }
}
