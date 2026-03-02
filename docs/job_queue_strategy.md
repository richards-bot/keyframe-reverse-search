# Job Queue Strategy (Production)

Current app now includes an in-memory queue (`InMemoryJobQueue`) for local/dev, replacing ad-hoc FastAPI background tasks.

## Why this is still not enough for production
- Jobs are lost on process restart
- No cross-instance coordination
- No retry policy persistence
- No dead-letter queue

## Recommended production architecture

### Option A (best fit): Redis + RQ/Celery/Arq
1. API receives submission, writes record with `queued`
2. API pushes job id to Redis-backed queue
3. Dedicated workers pull jobs and process keyframes/search/report
4. Worker updates submission status atomically
5. Retries with exponential backoff on transient errors
6. Dead-letter queue for exhausted retries

### Option B: SQS + Lambda/ECS workers
- Good for AWS-native deployments and burst traffic

## Reliability requirements
- Idempotent job execution by `submission_id`
- Status transitions validated (`queued -> processing -> done|failed`)
- Store structured error codes/messages
- Queue depth + processing latency metrics
- Alerting on failed-job rate

## Suggested next implementation step
Introduce `JobQueue` interface and swap in Redis implementation behind env flag:
- `QUEUE_BACKEND=inmemory|redis`
- `REDIS_URL=...`

This keeps local UX simple while allowing production durability.
