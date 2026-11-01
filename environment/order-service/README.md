# order-service

Order intake and status tracking for the orderflow shop. Spring Boot 3.5,
Java 21, Postgres for state, Redis for the read cache, Kafka for events.

Docs:

- `docs/API.md`, the HTTP contract. Clients depend on every line of it.
- `docs/ARCHITECTURE.md`, how the pieces fit, what the Kafka topics promise,
  what the service is supposed to do with status events.
- `tools/README.md`, scripts for exercising a local stack.

## Build and test

```
mvn -q test            # unit tests, no infrastructure needed
mvn -q -DskipTests package
```

## Run the full stack

From the parent `environment/` directory:

```
docker compose up -d --build
curl -s localhost:58080/actuator/health
```

Service is on 58080, Postgres on 55432, Redis on 56379, Kafka (external
listener) on 59094.

## Layout

```
src/main/java/com/orderflow
  api/         controller, request/response records, error mapping
  service/     OrderService (create), OrderQueryService (read + cache), OrderStatusService (apply events)
  messaging/   Kafka publisher and consumer, event records
  domain/      JPA entities and repositories
  config/      Kafka, Redis cache, Clock beans
src/main/resources/db/migration   Flyway migrations
```

## Conventions

- Entities don't leak out of the service layer; controllers return the records
  in `api/`.
- Schema changes go in a new Flyway migration. Never edit a migration that has
  shipped.
- `Clock` is injected everywhere we need the time so tests can pin it.
