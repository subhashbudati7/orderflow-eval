package com.orderflow.api;

import com.orderflow.service.IdempotencyKeyReusedException;
import com.orderflow.service.OrderNotFoundException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;

@RestControllerAdvice
public class ApiErrors {

    public record ErrorBody(String code, String message) {
    }

    @ExceptionHandler(OrderNotFoundException.class)
    ResponseEntity<ErrorBody> notFound(OrderNotFoundException e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(new ErrorBody("ORDER_NOT_FOUND", e.getMessage()));
    }

    @ExceptionHandler(IdempotencyKeyReusedException.class)
    ResponseEntity<ErrorBody> keyReused(IdempotencyKeyReusedException e) {
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
                .body(new ErrorBody("IDEMPOTENCY_KEY_REUSED", e.getMessage()));
    }

    @ExceptionHandler(MissingRequestHeaderException.class)
    ResponseEntity<ErrorBody> missingHeader(MissingRequestHeaderException e) {
        return ResponseEntity.badRequest()
                .body(new ErrorBody("MISSING_HEADER", e.getHeaderName() + " header is required"));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<Map<String, Object>> invalid(MethodArgumentNotValidException e) {
        var fields = e.getBindingResult().getFieldErrors().stream()
                .map(f -> f.getField() + ": " + f.getDefaultMessage())
                .toList();
        return ResponseEntity.badRequest()
                .body(Map.of("code", "VALIDATION_FAILED", "errors", fields));
    }
}
