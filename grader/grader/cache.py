import redis


class Cache:
    PREFIX = "orderflow:orders::"

    def __init__(self, url: str):
        self.client = redis.Redis.from_url(url)

    def close(self) -> None:
        self.client.close()

    def reset(self) -> None:
        self.client.flushall()

    def has_order(self, order_id: str) -> bool:
        return self.client.exists(self.PREFIX + order_id) == 1

    def raw_order(self, order_id: str) -> bytes | None:
        return self.client.get(self.PREFIX + order_id)
