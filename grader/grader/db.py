"""Direct Postgres access. The database is the source of truth; several
scenarios assert against it on purpose so a cache bug can't hide a write bug
(or the other way round)."""
import psycopg


class Db:
    def __init__(self, dsn: str):
        self.conn = psycopg.connect(dsn, autocommit=True)

    def close(self) -> None:
        self.conn.close()

    def reset(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE order_status_history, orders")

    def count_orders_for_key(self, key: str) -> int:
        with self.conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM orders WHERE idempotency_key = %s", (key,))
            return cur.fetchone()[0]

    def order(self, order_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT status, last_event_sequence, status_updated_at FROM orders WHERE id = %s",
                (order_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return {"status": row[0], "lastEventSequence": row[1], "statusUpdatedAt": row[2]}

    def history_sequences(self, order_id: str) -> list[int]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT event_sequence FROM order_status_history WHERE order_id = %s ORDER BY id",
                (order_id,),
            )
            return [r[0] for r in cur.fetchall()]

    def has_unique_idempotency_index(self) -> bool:
        """Diagnostic only, not scored. Tells us how the candidate fixed duplicates."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM pg_indexes
                WHERE tablename = 'orders' AND indexdef ILIKE '%%UNIQUE%%'
                  AND indexdef ILIKE '%%idempotency_key%%'
                """
            )
            return cur.fetchone()[0] > 0
