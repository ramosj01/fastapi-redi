from redis.asyncio import ConnectionPool, Redis


def create_redis(url: str, max_connections: int) -> Redis:
    pool = ConnectionPool.from_url(
        url,
        max_connections=max_connections,
        decode_responses=True,
        health_check_interval=30,
        socket_connect_timeout=2,
        socket_timeout=2,
        retry_on_timeout=True,
    )
    return Redis(connection_pool=pool)
