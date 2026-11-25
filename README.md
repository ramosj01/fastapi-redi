# fastapi-redi

A horizontally scalable FastAPI service with a shared Redis cache, built on **clean architecture**.

## Architecture

```
app/
├── domain/            # Enterprise rules — pure Python, no framework imports
│   ├── entities/      #   Product entity + invariants
│   ├── repositories/  #   Repository ports (ABCs)
│   └── exceptions.py
├── application/       # Use cases — depend only on domain + ports
│   ├── interfaces/    #   Ports: CacheService, UnitOfWork, DistributedLock, RateLimiter
│   ├── dto/           #   Commands & DTOs (JSON-safe cache representation)
│   └── services/      #   ProductService (cache-aside reads, invalidating writes)
├── infrastructure/    # Adapters
│   ├── cache/         #   RedisCache, RedisLock, RedisRateLimiter
│   └── db/            #   SQLAlchemy async models, repository, unit of work
├── presentation/api/  # FastAPI routers, Pydantic schemas, middleware, error mapping
├── container.py       # Composition root (the only place wiring concretes to ports)
└── main.py            # App factory + lifespan
```

Dependencies point inward: `presentation → application → domain`, and
`infrastructure` implements the ports that `application` defines. Swapping Redis or
Postgres means writing a new adapter. The use cases don't change.

## Distributed design

| Concern | How it is handled |
|---|---|
| Stateless replicas | No in-process state. Cache, locks and rate limits all live in Redis. `docker compose` runs 3 API replicas behind nginx. |
| Shared cache | Cache-aside through `RedisCache`, with namespaced keys (`<prefix>:products:item:<id>`). |
| Cache stampede | On a miss, only the replica holding a Redis lock (`SET NX PX`) loads from the DB. The others poll for the value. |
| Cache penetration | Missing entities are cached with a short-TTL "miss" marker. |
| Invalidation | Writes commit to the DB first, then delete the item key. List caches are versioned (`products:list:v<N>:…`): one `INCR` invalidates every page without `SCAN`/`KEYS`. |
| Safe locks | Each lock carries a token, and a Lua script releases it only if the token matches, so a replica can't free a lock someone else holds. |
| Redis outage | The cache degrades to direct DB reads, and the rate limiter fails open. Requests keep working. |
| Rate limiting | A fixed-window counter in Redis, shared across replicas and keyed by the client IP from `X-Forwarded-For`. |
| Migrations | A one-shot `migrate` job runs Alembic once, before any replica starts. |
| Observability | JSON logs with `instance` and `request_id`. `X-Request-ID` is propagated and `X-Instance-ID` is added to every response. |
| Health | `/health/live` (process is up) and `/health/ready` (Redis + DB reachable; returns 503 when degraded, for the load balancer). |

## Run

```bash
docker compose up --build            # API on http://localhost:8000 (nginx → 3 replicas)
curl localhost:8000/health/ready
curl -XPOST localhost:8000/api/v1/products -H 'content-type: application/json' \
     -d '{"name":"Widget","sku":"W-1","price":"9.99","stock":5}'
```

Scale with `docker compose up --scale api=5`. Interactive docs are at `/docs`.

Local development:

```bash
uv sync
cp .env.example .env                 # point to your Postgres/Redis
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Tests

```bash
uv run pytest
```

- **Unit tests** cover the use cases with in-memory fakes, plus the cache, lock and rate limiter on fakeredis.
- **Integration tests** start two app instances that share one Redis and one database. They check that a write on one replica is seen immediately on the other.

## API

| Method | Path | |
|---|---|---|
| GET | `/api/v1/products?offset=&limit=` | list (cached, versioned) |
| GET | `/api/v1/products/{id}` | get (cached) |
| POST | `/api/v1/products` | create |
| PATCH | `/api/v1/products/{id}` | update (invalidates cache) |
| DELETE | `/api/v1/products/{id}` | delete (invalidates cache) |
