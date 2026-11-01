package com.orderflow.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.orderflow.api.OrderResponse;
import com.orderflow.service.OrderQueryService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;
import java.util.Map;

@Configuration
public class CacheConfig {

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory connectionFactory,
                                          ObjectMapper objectMapper,
                                          @Value("${orderflow.cache.orders-ttl}") Duration ordersTtl) {
        var valueSerializer = new Jackson2JsonRedisSerializer<>(objectMapper, OrderResponse.class);

        RedisCacheConfiguration ordersCache = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(ordersTtl)
                .prefixCacheNameWith("orderflow:")
                .serializeKeysWith(RedisSerializationContext.SerializationPair.fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair.fromSerializer(valueSerializer))
                .disableCachingNullValues();

        return RedisCacheManager.builder(connectionFactory)
                .withInitialCacheConfigurations(Map.of(OrderQueryService.ORDERS_CACHE, ordersCache))
                .build();
    }
}
