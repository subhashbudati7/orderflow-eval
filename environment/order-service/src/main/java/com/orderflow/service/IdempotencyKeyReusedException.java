package com.orderflow.service;

public class IdempotencyKeyReusedException extends RuntimeException {

    public IdempotencyKeyReusedException(String key) {
        super("Idempotency-Key '" + key + "' was already used with a different request body");
    }
}
