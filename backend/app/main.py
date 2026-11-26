import json
import logging
import math
import socket
import time
from contextlib import asynccontextmanager

import psycopg2
import redis
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field

from app.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "pod": socket.gethostname(),
            "version": settings.APP_VERSION,
            "message": record.getMessage(),
        }
        return json.dumps(log_record)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=settings.LOG_LEVEL, handlers=[handler], force=True)
logger = logging.getLogger("visit-counter-api")

# Prometheus Metrics (Week 10: Monitoring)
HTTP_REQUESTS_TOTAL = Counter(
    "visit_counter_http_requests_total",
    "Total HTTP requests processed",
    ["method", "endpoint", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "visit_counter_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
)
NOTES_CREATED_TOTAL = Counter(
    "visit_counter_notes_created_total",
    "Total guestbook notes persisted to PostgreSQL",
)


def get_redis_client():
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=2,
    )


def get_db_connection():
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        connect_timeout=3,
    )


def init_db(retries: int = 5, delay: int = 2):
    for attempt in range(1, retries + 1):
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS guestbook_notes (
                        id SERIAL PRIMARY KEY,
                        visitor_name VARCHAR(60) NOT NULL,
                        message VARCHAR(280) NOT NULL,
                        served_by_pod VARCHAR(100) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
            conn.commit()
            conn.close()
            logger.info("Database schema initialized successfully.")
            return
        except (psycopg2.Error, OSError) as exc:
            logger.warning("DB init attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(delay)
    logger.error("DB initialization failed after retries; relying on /readyz.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="K8s Production Visit Counter API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    endpoint = request.url.path
    if endpoint != "/metrics":
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(response.status_code),
        ).inc()
        HTTP_REQUEST_DURATION.labels(endpoint=endpoint).observe(elapsed)
    return response


class NoteCreate(BaseModel):
    visitor_name: str = Field(..., min_length=1, max_length=60)
    message: str = Field(..., min_length=1, max_length=280)


class NoteOut(BaseModel):
    id: int
    visitor_name: str
    message: str
    served_by_pod: str
    created_at: str


@app.get("/healthz")
def liveness_probe():
    """Kubernetes Liveness Probe: verifies process responsiveness."""
    return {
        "status": "alive",
        "pod": socket.gethostname(),
        "version": settings.APP_VERSION,
    }


@app.get("/readyz")
def readiness_probe():
    """Kubernetes Readiness Probe: verifies Redis and PostgreSQL connectivity."""
    status = {
        "redis": "down",
        "postgres": "down",
        "pod": socket.gethostname(),
        "version": settings.APP_VERSION,
    }
    try:
        if get_redis_client().ping():
            status["redis"] = "up"
    except (redis.RedisError, OSError) as exc:
        logger.error("Redis readiness failed: %s", exc)

    try:
        conn = get_db_connection()
        conn.close()
        status["postgres"] = "up"
    except (psycopg2.Error, OSError) as exc:
        logger.error("Postgres readiness failed: %s", exc)

    if status["redis"] != "up" or status["postgres"] != "up":
        raise HTTPException(status_code=503, detail=status)
    return {"status": "ready", **status}


@app.get("/metrics")
def metrics():
    """Prometheus scrape endpoint for Week 10 monitoring."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/visits")
def record_and_get_visits():
    """Increments Redis visit counter and returns recent PostgreSQL notes."""
    pod_name = socket.gethostname()

    try:
        total_visits = get_redis_client().incr("site_visit_count")
    except (redis.RedisError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"Redis error: {exc}") from exc

    notes: list[dict] = []
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, visitor_name, message, served_by_pod,
                       TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at
                FROM guestbook_notes
                ORDER BY id DESC
                LIMIT 10;
                """
            )
            notes = [dict(row) for row in cur.fetchall()]
        conn.close()
    except (psycopg2.Error, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"PostgreSQL error: {exc}") from exc

    return {
        "total_visits": total_visits,
        "served_by_pod": pod_name,
        "environment": settings.APP_ENV,
        "version": settings.APP_VERSION,
        "recent_notes": notes,
    }


@app.post("/api/notes", response_model=NoteOut, status_code=201)
def create_note(note: NoteCreate):
    """Persists a visitor note in PostgreSQL StatefulSet."""
    pod_name = socket.gethostname()
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO guestbook_notes (visitor_name, message, served_by_pod)
                VALUES (%s, %s, %s)
                RETURNING id, visitor_name, message, served_by_pod,
                          TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at;
                """,
                (note.visitor_name.strip(), note.message.strip(), pod_name),
            )
            created = dict(cur.fetchone())
        conn.commit()
        conn.close()
        NOTES_CREATED_TOTAL.inc()
        return created
    except (psycopg2.Error, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"Database write error: {exc}") from exc


@app.get("/api/load")
def simulate_cpu_load(iterations: int = Query(default=150000, ge=1000, le=2000000)):
    """Controlled CPU workload endpoint for live HPA autoscaling demos (Week 10)."""
    start = time.perf_counter()
    acc = 0.0
    for i in range(1, iterations):
        acc += math.sqrt(i)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    return {
        "status": "completed",
        "pod": socket.gethostname(),
        "iterations": iterations,
        "duration_ms": duration_ms,
        "checksum": round(acc, 2),
    }