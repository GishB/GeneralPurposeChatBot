import psycopg2


class AuditLogger:
    def __init__(self, dsn):
        self.dsn = dsn

    def log(self, **kwargs):
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_request_audit
                    (time_in, time_out, user_id, source_name, request_id, query_in, response_out, status, execution_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        kwargs["time_in"],
                        kwargs["time_out"],
                        kwargs["user_id"],
                        kwargs["source_name"],
                        kwargs["request_id"],
                        kwargs["query_in"],
                        kwargs["response_out"],
                        kwargs["status"],
                        kwargs["execution_time"],
                    ),
                )
